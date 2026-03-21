"""
Smart model routing for FinClosePilot.
Routes LLM calls to the cheapest model that can handle the task complexity.
Tracks all usage for cost efficiency reporting.
"""
import time
import logging
from typing import Optional

import google.generativeai as genai
from backend.config import GEMINI_API_KEY
from backend.database.audit_logger import log_model_usage

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# ─── Task → Model Routing Table ──────────────────────────────────────────────
TASK_ROUTING: dict[str, str] = {
    # Simple (Flash 1.5 — fastest, cheapest)
    "data_normalisation":        "gemini-1.5-flash",
    "date_formatting":           "gemini-1.5-flash",
    "vendor_name_extraction":    "gemini-1.5-flash",
    "amount_parsing":            "gemini-1.5-flash",
    "narration_cleaning":        "gemini-1.5-flash",

    # Medium (Flash 2.0 — default)
    "duplicate_detection_reasoning": "gemini-2.0-flash",
    "anomaly_classification":    "gemini-2.0-flash",
    "variance_narrative":        "gemini-2.0-flash",
    "audit_query_response":      "gemini-2.0-flash",

    # Complex (Pro 1.5 — best reasoning)
    "regulatory_reasoning":          "gemini-1.5-pro",
    "guardrail_conflict_resolution": "gemini-1.5-pro",
    "indas_110_elimination_narrative": "gemini-1.5-pro",
    "tax_optimisation_analysis":     "gemini-1.5-pro",
    "escalation_reasoning":          "gemini-1.5-pro",
    "benford_violation_forensics":   "gemini-1.5-pro",

    # Zero LLM — pure Python (free)
    "benford_calculation":     "PYTHON_ONLY",
    "chi_squared_test":        "PYTHON_ONLY",
    "amount_arithmetic":       "PYTHON_ONLY",
    "percentage_calculation":  "PYTHON_ONLY",
    "duplicate_fuzzy_match":   "PYTHON_ONLY",
    "indas_110_math":          "PYTHON_ONLY",
}

# Estimated cost per 1K tokens (USD) — for reporting
MODEL_COST_PER_1K: dict[str, float] = {
    "gemini-1.5-flash":  0.000075,
    "gemini-2.0-flash":  0.00010,
    "gemini-1.5-pro":    0.00125,
    "PYTHON_ONLY":       0.0,
}

# In-memory stats accumulator (per process lifetime)
_run_stats: dict[str, dict] = {}


def _get_or_create_stats(run_id: str) -> dict:
    if run_id not in _run_stats:
        _run_stats[run_id] = {
            "calls_by_model": {},
            "tokens_by_model": {},
            "python_only_calls": 0,
            "total_latency_ms": 0,
        }
    return _run_stats[run_id]


async def route_call(
    task_type: str,
    system_prompt: str,
    user_message: str,
    run_id: str = "unknown",
) -> dict:
    """
    Routes LLM call to the correct model based on TASK_ROUTING.
    For PYTHON_ONLY tasks: raises ValueError (caller must use Python directly).

    Returns:
    {
      "response": str,
      "model_used": str,
      "tokens_used": int or None,
      "task_type": str,
      "latency_ms": int
    }
    """
    model_name = TASK_ROUTING.get(task_type, "gemini-2.0-flash")

    if model_name == "PYTHON_ONLY":
        # Track as python-only call
        stats = _get_or_create_stats(run_id)
        stats["python_only_calls"] += 1
        stats["calls_by_model"]["PYTHON_ONLY"] = stats["calls_by_model"].get("PYTHON_ONLY", 0) + 1
        log_model_usage(run_id, task_type, "PYTHON_ONLY", 0, 0)
        raise ValueError(
            f"Task '{task_type}' is routed to PYTHON_ONLY — "
            "caller must handle with pure Python, not LLM."
        )

    # Try the designated model; fall back to gemini-2.0-flash if Pro unavailable
    start = time.perf_counter()
    try:
        model = genai.GenerativeModel(model_name)
        full_prompt = f"{system_prompt}\n\n{user_message}"
        response = model.generate_content(full_prompt)
        response_text = response.text
    except Exception as e:
        if model_name == "gemini-1.5-pro":
            logger.warning(
                f"[ModelRouter] Pro model unavailable for '{task_type}', "
                f"using Flash fallback. Error: {e}"
            )
            model_name = "gemini-2.0-flash"
            try:
                model = genai.GenerativeModel(model_name)
                full_prompt = f"{system_prompt}\n\n{user_message}"
                response = model.generate_content(full_prompt)
                response_text = response.text
            except Exception as e2:
                logger.error(f"[ModelRouter] Fallback also failed: {e2}")
                raise
        else:
            raise

    latency_ms = int((time.perf_counter() - start) * 1000)
    tokens_used = None
    try:
        tokens_used = response.usage_metadata.total_token_count
    except Exception:
        # Estimate tokens from text length
        tokens_used = max(len(full_prompt) // 4, 1) + max(len(response_text) // 4, 1)

    # Track stats
    stats = _get_or_create_stats(run_id)
    stats["calls_by_model"][model_name] = stats["calls_by_model"].get(model_name, 0) + 1
    stats["tokens_by_model"][model_name] = stats["tokens_by_model"].get(model_name, 0) + (tokens_used or 0)
    stats["total_latency_ms"] += latency_ms

    # Persist to SQLite
    try:
        log_model_usage(run_id, task_type, model_name, tokens_used, latency_ms)
    except Exception:
        pass  # non-fatal

    logger.info(
        f"[ModelRouter] {task_type} → {model_name} | "
        f"{tokens_used} tokens | {latency_ms}ms"
    )

    return {
        "response":    response_text,
        "model_used":  model_name,
        "tokens_used": tokens_used,
        "task_type":   task_type,
        "latency_ms":  latency_ms,
    }


def get_routing_stats(run_id: str = None) -> dict:
    """
    Returns cost efficiency metrics for the current or specified run.
    {
      "calls_by_model": {"gemini-1.5-flash": 45, ...},
      "python_only_calls": 12,
      "estimated_cost_usd": float,
      "estimated_cost_if_all_pro": float,
      "cost_savings_pct": float,
      "routing_summary": str
    }
    """
    # Use in-memory stats if available, otherwise query DB
    if run_id and run_id in _run_stats:
        stats = _run_stats[run_id]
    else:
        try:
            from backend.database.audit_logger import get_model_usage_stats
            db_stats = get_model_usage_stats(run_id)
            stats = {
                "calls_by_model": db_stats.get("calls_by_model", {}),
                "tokens_by_model": db_stats.get("total_tokens_by_model", {}),
                "python_only_calls": db_stats.get("python_only_calls", 0),
            }
        except Exception:
            stats = {"calls_by_model": {}, "tokens_by_model": {}, "python_only_calls": 0}

    calls = stats.get("calls_by_model", {})
    tokens = stats.get("tokens_by_model", {})
    python_only = stats.get("python_only_calls", 0)

    # Calculate costs
    estimated_cost = 0.0
    total_tokens_all = 0
    for model, token_count in tokens.items():
        rate = MODEL_COST_PER_1K.get(model, 0.0001)
        estimated_cost += (token_count / 1000) * rate
        total_tokens_all += token_count

    # Cost if everything used Pro
    pro_rate = MODEL_COST_PER_1K["gemini-1.5-pro"]
    cost_if_all_pro = (total_tokens_all / 1000) * pro_rate if total_tokens_all > 0 else 0.01

    savings_pct = (
        round((1 - estimated_cost / cost_if_all_pro) * 100, 1)
        if cost_if_all_pro > 0 else 0.0
    )

    total_calls = sum(calls.values())
    flash_calls = calls.get("gemini-1.5-flash", 0)
    flash_pct = round(flash_calls / max(total_calls, 1) * 100)

    return {
        "calls_by_model":          calls,
        "python_only_calls":       python_only,
        "estimated_cost_usd":      round(estimated_cost, 6),
        "estimated_cost_if_all_pro": round(cost_if_all_pro, 6),
        "cost_savings_pct":        savings_pct,
        "routing_summary": (
            f"{flash_pct}% of calls used Flash tier | "
            f"{python_only} calculations used pure Python"
        ),
    }
