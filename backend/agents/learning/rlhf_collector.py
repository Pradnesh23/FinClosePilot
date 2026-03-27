"""
RLHF Signal Collector — captures human corrections from CFO overrides.
"""

import logging
import json
from datetime import datetime
from backend.database.audit_logger import save_rlhf_signal # type: ignore
from backend.memory import letta_client as letta # type: ignore

logger = logging.getLogger(__name__)


async def collect_cfo_override(
    run_id: str,
    guardrail_fire_id: int,
    original_fire: dict,
    override_reason: str,
    corrected_by: str,
    letta_client_,
    agent_id: str,
) -> dict:
    """
    Record a CFO override of a SOFT_FLAG guardrail rule.
    HARD_BLOCKs cannot be overridden.
    """
    if original_fire.get("rule_level") == "HARD_BLOCK":
        return {
            "success": False,
            "error": "Hard blocks cannot be overridden — regulatory violation.",
        }

    signal = {
        "run_id": run_id,
        "guardrail_fire_id": guardrail_fire_id,
        "signal_type": "CFO_OVERRIDE",
        "original_output": original_fire,
        "correction": "override_approved",
        "correction_reason": override_reason,
        "corrected_by": corrected_by,
    }

    # Save to SQLite
    save_rlhf_signal(run_id, signal)

    # Store to Letta archival for future learning
    await letta.store_rlhf_signal(letta_client_, agent_id, {
        "type": "cfo_override",
        "rule_id": original_fire.get("rule_id"),
        "vendor_name": original_fire.get("vendor_name"),
        "amount": original_fire.get("amount_inr"),
        "reason": override_reason,
        "corrected_by": corrected_by,
        "timestamp": datetime.utcnow().isoformat(),
    })

    logger.info(f"[RLHF] CFO override recorded: {original_fire.get('rule_id')} by {corrected_by}")
    return {"success": True, "signal_type": "CFO_OVERRIDE"}


async def collect_anomaly_feedback(
    run_id: str,
    anomaly_id: int,
    is_valid: bool,
    feedback_notes: str,
    corrected_by: str,
    letta_client_,
    agent_id: str,
) -> dict:
    """Record human feedback on anomaly classification."""
    signal = {
        "run_id": run_id,
        "signal_type": "ANOMALY_FEEDBACK",
        "original_output": {"anomaly_id": anomaly_id, "validated": is_valid},
        "correction": "valid" if is_valid else "false_positive",
        "correction_reason": feedback_notes,
        "corrected_by": corrected_by,
    }

    save_rlhf_signal(run_id, signal)
    await letta.store_rlhf_signal(letta_client_, agent_id, {
        "type": "anomaly_feedback",
        "anomaly_id": anomaly_id,
        "is_valid": is_valid,
        "notes": feedback_notes,
    })

    return {"success": True, "signal_type": "ANOMALY_FEEDBACK"}
