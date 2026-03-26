"""
Smart model routing for FinClosePilot.
Routes LLM calls to Groq, OpenRouter, or Gemini natively depending on what keys are available.
Tracks all usage for cost efficiency reporting.
"""
import time
import json
import logging
from typing import Optional

from backend.config import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY
from backend.database.audit_logger import log_model_usage

logger = logging.getLogger(__name__)

# Initialize clients if keys exist
clients = {}

if GROQ_API_KEY:
    from openai import AsyncOpenAI
    clients["groq"] = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

if OPENROUTER_API_KEY:
    from openai import AsyncOpenAI
    clients["openrouter"] = AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

if GEMINI_API_KEY:
    from google import genai
    clients["gemini"] = genai.Client(api_key=GEMINI_API_KEY)


# Determine primary provider (priority: openrouter -> groq -> gemini)
PRIMARY_PROVIDER = None
if OPENROUTER_API_KEY:
    PRIMARY_PROVIDER = "openrouter"
elif GROQ_API_KEY:
    PRIMARY_PROVIDER = "groq"
elif GEMINI_API_KEY:
    PRIMARY_PROVIDER = "gemini"


# ─── Task → Model Routing Table ──────────────────────────────────────────────
# We define model names per provider
PROVIDER_MODELS = {
    "openrouter": {
        "flash": "google/gemini-2.0-flash-001",
        "pro": "meta-llama/llama-3.3-70b-instruct",
    },
    "groq": {
        "flash": "llama-3.3-70b-versatile",
        "pro": "deepseek-r1-distill-llama-70b",
    },
    "gemini": {
        "flash": "gemini-2.0-flash",
        "pro": "gemini-1.5-pro",
    }
}

# Assign complexity tier to each task
TASK_COMPLEXITY: dict[str, str] = {
    "data_normalisation":        "flash",
    "date_formatting":           "flash",
    "vendor_name_extraction":    "flash",
    "amount_parsing":            "flash",
    "narration_cleaning":        "flash",
    "anomaly_classification":    "flash",
    "variance_narrative":        "flash",
    "audit_query_response":      "flash",
    "duplicate_detection_reasoning": "flash",

    "regulatory_reasoning":          "pro",
    "guardrail_conflict_resolution": "pro",
    "indas_110_elimination_narrative": "pro",
    "tax_optimisation_analysis":     "pro",
    "escalation_reasoning":          "pro",
    "benford_violation_forensics":   "pro",

    # Zero LLM — pure Python (free)
    "benford_calculation":     "PYTHON_ONLY",
    "chi_squared_test":        "PYTHON_ONLY",
    "amount_arithmetic":       "PYTHON_ONLY",
    "percentage_calculation":  "PYTHON_ONLY",
    "duplicate_fuzzy_match":   "PYTHON_ONLY",
    "indas_110_math":          "PYTHON_ONLY",
}

# Estimated cost per 1K tokens (USD)
MODEL_COST_PER_1K: dict[str, float] = {
    "gemini-1.5-flash": 0.000075,
    "gemini-2.0-flash": 0.00010,
    "gemini-1.5-pro":   0.00125,
    "google/gemini-2.0-flash-exp:free": 0.0,
    "meta-llama/llama-3.3-70b-instruct:free": 0.0,
    "llama-3.3-70b-versatile": 0.0,
    "deepseek-r1-distill-llama-70b": 0.0,
    "PYTHON_ONLY": 0.0,
}


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


async def _call_openai_compatible(client, model_name: str, system_prompt: str, user_message: str, force_json: bool = False) -> tuple[str, int]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    if force_json and "json" not in system_prompt.lower():
        messages[0]["content"] += "\nReturn ONLY valid JSON. No markdown."
        if "groq" in str(client.base_url):
            kwargs = {"response_format": {"type": "json_object"}}
        else:
            kwargs = {}
    else:
        kwargs = {}

    response = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.1,
        **kwargs
    )
    tokens = response.usage.total_tokens if response.usage else 0
    return response.choices[0].message.content, tokens


async def _call_gemini_native(model_name: str, system_prompt: str, user_message: str, force_json: bool = False) -> tuple[str, int]:
    client = clients.get("gemini")
    if not client:
        raise ValueError("Gemini client not initialized")
        
    full_prompt = f"{system_prompt}\n\nUser: {user_message}"
    if force_json:
        full_prompt += "\n\nCRITICAL: Return ONLY valid JSON. No markdown backticks."
    
    response = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
    )
    
    tokens = getattr(response.usage_metadata, "total_token_count", 0) if response.usage_metadata else 0
    return response.text, tokens


def _clean_json(text: str) -> str:
    """Strips markdown backticks and extra noise from LLM JSON strings."""
    text = text.strip()
    if text.startswith("```"):
        # Remove starting ```json or ```
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        # Remove ending ```
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


async def route_call(
    task_type: str,
    system_prompt: str,
    user_message: str,
    run_id: str = "unknown",
    force_json: bool = False
) -> dict:
    """
    Routes LLM call to the correct model and active provider.
    """
    if not PRIMARY_PROVIDER:
        raise ValueError("No API keys found! Please set OPENROUTER_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY")

    complexity = TASK_COMPLEXITY.get(task_type, "flash")

    if complexity == "PYTHON_ONLY":
        stats = _get_or_create_stats(run_id)
        stats["python_only_calls"] += 1
        stats["calls_by_model"]["PYTHON_ONLY"] = stats["calls_by_model"].get("PYTHON_ONLY", 0) + 1
        log_model_usage(run_id, task_type, "PYTHON_ONLY", 0, 0)
        raise ValueError(f"Task '{task_type}' is routed to PYTHON_ONLY")

    model_name = PROVIDER_MODELS[PRIMARY_PROVIDER].get(complexity, "flash")

    start_time = time.perf_counter()
    tokens_used = 0
    
    try:
        if PRIMARY_PROVIDER in ["openrouter", "groq"]:
            response_text, tokens_used = await _call_openai_compatible(
                clients[PRIMARY_PROVIDER], model_name, system_prompt, user_message, force_json
            )
        else:
            response_text, tokens_used = await _call_gemini_native(
                model_name, system_prompt, user_message, force_json
            )
        
        if force_json:
            response_text = _clean_json(response_text)
    except Exception as e:
        logger.error(f"[ModelRouter] Failed using {PRIMARY_PROVIDER} model {model_name}: {e}")
        
        # Cross-provider fallback: try ALL other available providers
        fallback_providers = [p for p in clients.keys() if p != PRIMARY_PROVIDER]
        response_text = None
        
        for fb_provider in fallback_providers:
            try:
                fb_model = PROVIDER_MODELS.get(fb_provider, {}).get(complexity, PROVIDER_MODELS.get(fb_provider, {}).get("flash"))
                if not fb_model:
                    continue
                logger.warning(f"[ModelRouter] Falling back to {fb_provider} → {fb_model}")
                model_name = fb_model  # update for stats tracking
                
                if fb_provider in ["openrouter", "groq"]:
                    response_text, tokens_used = await _call_openai_compatible(
                        clients[fb_provider], fb_model, system_prompt, user_message, force_json
                    )
                else:
                    response_text, tokens_used = await _call_gemini_native(
                        fb_model, system_prompt, user_message, force_json
                    )
                
                if force_json and response_text:
                    response_text = _clean_json(response_text)
                break  # success
            except Exception as fb_e:
                logger.error(f"[ModelRouter] Fallback {fb_provider} also failed: {fb_e}")
                continue
        
        if response_text is None:
            raise  # all providers failed

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # Track stats
    stats = _get_or_create_stats(run_id)
    stats["calls_by_model"][model_name] = stats["calls_by_model"].get(model_name, 0) + 1
    stats["tokens_by_model"][model_name] = stats["tokens_by_model"].get(model_name, 0) + tokens_used
    stats["total_latency_ms"] += latency_ms

    try:
        log_model_usage(run_id, task_type, model_name, tokens_used, latency_ms)
    except Exception:
        pass

    logger.info(f"[{PRIMARY_PROVIDER.upper()}] {task_type} → {model_name} | {tokens_used} tokens | {latency_ms}ms")

    return {
        "response":    response_text,
        "model_used":  model_name,
        "tokens_used": tokens_used,
        "task_type":   task_type,
        "latency_ms":  latency_ms,
    }


def get_routing_stats(run_id: str = None) -> dict:
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

    estimated_cost = sum((tok / 1000) * MODEL_COST_PER_1K.get(m, 0.0) for m, tok in tokens.items())
    total_tokens_all = sum(tokens.values())
    
    pro_rate = 0.00125 # standard gemini-1.5-pro benchmark cost
    cost_if_all_pro = (total_tokens_all / 1000) * pro_rate if total_tokens_all > 0 else 0.01
    savings_pct = round((1 - estimated_cost / cost_if_all_pro) * 100, 1) if cost_if_all_pro > 0 else 0.0
    
    total_calls = sum(calls.values())
    flash_calls = sum(v for k, v in calls.items() if "flash" in k or "versatile" in k)
    flash_pct = round(flash_calls / max(total_calls, 1) * 100)

    return {
        "calls_by_model":          calls,
        "python_only_calls":       python_only,
        "estimated_cost_usd":      round(estimated_cost, 6),
        "estimated_cost_if_all_pro": round(cost_if_all_pro, 6),
        "cost_savings_pct":        savings_pct,
        "routing_summary": f"{PRIMARY_PROVIDER.title()}: {flash_pct}% of calls used Fast tier | {python_only} pure Python skips"
    }
