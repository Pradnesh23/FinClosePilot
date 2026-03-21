"""
Predictive Close Timeline Agent — predicts when pipeline will complete.
"""

import logging
import json
from datetime import datetime, timedelta, timezone
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Predictive Close Timeline Agent for FinClosePilot.

Given current pipeline progress and historical close data, predict:
1. Total time to complete this close
2. Which step is the current bottleneck
3. What is blocking completion
4. Confidence level of prediction

Use historical patterns from Letta memory to calibrate predictions.
Compare current progress rate against past close cycles.

Return ONLY valid JSON:
{
  "predicted_completion_minutes": int,
  "predicted_completion_time": "ISO8601",
  "confidence": 0.0-1.0,
  "current_bottleneck": "string",
  "bottleneck_reason": "string",
  "steps_complete": int,
  "steps_remaining": int,
  "time_per_step_historical_avg": float,
  "risk_factors": ["string"],
  "on_track": bool
}
"""

PIPELINE_STEPS = [
    "INGESTING", "RECONCILING", "DETECTING_ANOMALIES", "CRITIC_CHECK",
    "ENFORCING_GUARDRAILS", "GENERATING_REPORTS", "FORM26AS_RECON",
    "CONSOLIDATION", "PREDICTIVE_TIMELINE", "REGULATORY_CHECK",
    "TELEGRAM_NOTIFICATIONS", "COMPLETE",
]


async def predict_close_timeline(
    current_state: dict,
    letta_client,
    agent_id: str,
) -> dict:
    """Predict remaining time to close completion."""
    # Fetch historical patterns from Letta
    history = await letta.get_period_patterns(letta_client, agent_id, "close_duration")
    historical_minutes = []
    for h in history:
        if isinstance(h, dict) and "total_minutes" in h:
            historical_minutes.append(float(h["total_minutes"]))
    historical_avg = sum(historical_minutes) / len(historical_minutes) if historical_minutes else 18.0

    current_step = current_state.get("current_step", "INGESTING")
    steps_done = PIPELINE_STEPS.index(current_step) if current_step in PIPELINE_STEPS else 0
    steps_remaining = len(PIPELINE_STEPS) - steps_done - 1

    elapsed = current_state.get("elapsed_seconds", 0)
    rate_per_step = elapsed / max(steps_done, 1)
    predicted_remaining = rate_per_step * steps_remaining

    user_msg = json.dumps({
        "current_step": current_step,
        "steps_complete": steps_done,
        "steps_remaining": steps_remaining,
        "elapsed_seconds": elapsed,
        "historical_avg_minutes": historical_avg,
        "pending_approvals": current_state.get("pending_approvals", []),
        "hard_blocks": current_state.get("hard_blocks", 0),
        "rate_per_step_seconds": rate_per_step,
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        result["historical_avg_minutes"] = historical_avg
        result["elapsed_seconds"] = elapsed
        return result
    except Exception as e:
        logger.error(f"[PredictiveClose] Failed: {e}")
        now = datetime.now(timezone.utc)
        predicted = now + timedelta(seconds=predicted_remaining)
        return {
            "predicted_completion_minutes": int(predicted_remaining / 60),
            "predicted_completion_time": predicted.isoformat(),
            "confidence": 0.7,
            "current_bottleneck": current_step,
            "bottleneck_reason": "Processing in progress",
            "steps_complete": steps_done,
            "steps_remaining": steps_remaining,
            "time_per_step_historical_avg": historical_avg / max(len(PIPELINE_STEPS), 1),
            "risk_factors": ["CFO approval pending"] if current_state.get("hard_blocks", 0) > 0 else [],
            "on_track": elapsed < historical_avg * 60,
        }


async def update_prediction(
    run_id: str,
    step_completed: str,
    letta_client,
    agent_id: str,
) -> dict:
    """Re-calculate prediction after a step completes."""
    from backend.database.models import get_db_connection
    conn = get_db_connection()
    try:
        run_row = conn.execute(
            "SELECT created_at FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if run_row:
            created_at = datetime.fromisoformat(run_row["created_at"])
            elapsed = (datetime.utcnow() - created_at).total_seconds()
        else:
            elapsed = 0
    finally:
        conn.close()

    current_state = {
        "current_step": step_completed,
        "elapsed_seconds": elapsed,
    }
    return await predict_close_timeline(current_state, letta_client, agent_id)


async def store_close_duration(
    run_id: str,
    step_name: str,
    duration_seconds: int,
    letta_client,
    agent_id: str,
) -> None:
    """Store step duration to Letta for future predictions."""
    await letta.store_to_archival(letta_client, agent_id, {
        "type": "close_duration",
        "run_id": run_id,
        "step": step_name,
        "duration_seconds": duration_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
