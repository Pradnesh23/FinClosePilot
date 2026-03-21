"""
Confidence threshold and escalation system for FinClosePilot.
Used by ALL agents to decide whether to proceed autonomously or escalate.
"""
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Thresholds ───────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLDS: dict[str, float] = {
    "reconciliation_root_cause": 0.75,
    "anomaly_classification":    0.80,
    "guardrail_enforcement":      0.90,  # highest — legal implications
    "variance_narrative":          0.78,
    "tax_opportunity":             0.72,
    "form26as_mismatch":           0.76,
    "duplicate_detection":         0.85,
    "regulatory_extraction":       0.80,
}

# ─── Escalation Reasons ───────────────────────────────────────────────────────
ESCALATION_REASONS: dict[str, str] = {
    "LOW_CONFIDENCE":           "Agent confidence below threshold — human review required",
    "CONFLICTING_RULES":        "Two or more guardrail rules fire with conflicting actions",
    "NO_PRIOR_PATTERN":         "No historical data in Letta memory for this pattern",
    "AMBIGUOUS_NARRATION":      "Transaction narration insufficient to classify reliably",
    "JURISDICTION_UNKNOWN":     "Regulatory jurisdiction not in agent knowledge base",
    "AMOUNT_EXCEEDS_POLICY":    "Transaction amount exceeds autonomous action limit",
    "MULTI_FRAMEWORK_CONFLICT": "GST and IndAS rules conflict on same transaction",
    "BORDERLINE_STATISTIC":     "Statistical result is near significance threshold",
    "SMALL_SAMPLE":             "Sample size below minimum for reliable inference",
    "NEW_VENDOR_HIGH_AMOUNT":   "New vendor with no history and high transaction amount",
    "REPEATED_BREAKS":          "Same vendor has 3+ breaks in the same period",
    "INVALID_GSTIN_HIGH_AMOUNT":"Invalid or missing GSTIN on high-value transaction",
}

# Amount policy limit for autonomous action (in INR)
AUTONOMOUS_AMOUNT_LIMIT = 5_00_000  # Rs 5 Lakh


# ─── Core Functions ───────────────────────────────────────────────────────────

def check_confidence(output: dict, agent_type: str) -> dict:
    """
    Checks if agent output confidence meets threshold for that agent type.

    Returns:
    {
      "should_proceed": bool,
      "confidence": float,
      "threshold": float,
      "escalation_required": bool,
      "escalation_reason": str or None,
      "escalation_level": "HUMAN_REVIEW|CFO|LEGAL|AUTO_PROCEED",
      "partial_action_allowed": bool,
      "low_confidence_items": [{"item": str, "confidence": float, "reason": str}]
    }
    """
    threshold = CONFIDENCE_THRESHOLDS.get(agent_type, 0.75)
    confidence = float(output.get("confidence", 0.0))

    # Check for a list of items with individual confidence scores
    items = output.get("items", [])
    low_confidence_items = []
    for item in items:
        item_conf = float(item.get("confidence", confidence))
        if item_conf < threshold:
            low_confidence_items.append({
                "item":       str(item.get("id", item.get("description", "unknown"))),
                "confidence": item_conf,
                "reason":     item.get("reasoning", "Confidence below threshold"),
            })

    # Escalation level based on agent type and delta
    gap = threshold - confidence
    if confidence >= threshold:
        escalation_level = "AUTO_PROCEED"
        escalation_required = False
        escalation_reason = None
    elif gap <= 0.10:
        escalation_level = "HUMAN_REVIEW"
        escalation_required = True
        escalation_reason = "LOW_CONFIDENCE"
    elif agent_type == "guardrail_enforcement":
        escalation_level = "LEGAL"
        escalation_required = True
        escalation_reason = "LOW_CONFIDENCE"
    else:
        escalation_level = "CFO"
        escalation_required = True
        escalation_reason = "LOW_CONFIDENCE"

    # Partial proceed allowed if SOME items are high-confidence
    partial_action_allowed = (
        len(low_confidence_items) > 0
        and len(low_confidence_items) < len(items)
        and escalation_level != "LEGAL"
    )

    return {
        "should_proceed":         not escalation_required,
        "confidence":             confidence,
        "threshold":              threshold,
        "escalation_required":    escalation_required,
        "escalation_reason":      escalation_reason,
        "escalation_level":       escalation_level,
        "partial_action_allowed": partial_action_allowed,
        "low_confidence_items":   low_confidence_items,
    }


async def escalate(
    item: dict,
    reason_code: str,
    agent_type: str,
    letta_client,
    agent_id: str,
    run_id: str,
    confidence: float = 0.0,
    threshold: float = 0.75,
    escalation_level: str = "HUMAN_REVIEW",
) -> dict:
    """
    Creates a structured escalation record.
    Stores to Letta archival memory.
    Logs to SQLite escalations table.
    Sends Telegram notification if escalation_level is CFO or LEGAL.
    """
    reason_text = ESCALATION_REASONS.get(reason_code, reason_code)
    escalation_id = f"ESC-{run_id[:8]}-{agent_type[:4].upper()}-{datetime.utcnow().strftime('%H%M%S')}"

    record = {
        "escalation_id":    escalation_id,
        "run_id":           run_id,
        "agent_type":       agent_type,
        "reason_code":      reason_code,
        "reason_text":      reason_text,
        "confidence":       confidence,
        "threshold":        threshold,
        "escalation_level": escalation_level,
        "item":             item,
        "resolved":         False,
        "created_at":       datetime.utcnow().isoformat(),
    }

    # 1. Log to SQLite
    try:
        from backend.database.audit_logger import log_escalation
        log_escalation(record)
    except Exception as e:
        logger.error(f"[Escalation] SQLite log failed: {e}")

    # 2. Store in Letta archival memory
    try:
        if letta_client and agent_id:
            from backend.memory.letta_client import store_escalation
            await store_escalation(letta_client, agent_id, record)
    except Exception as e:
        logger.warning(f"[Escalation] Letta store failed (non-fatal): {e}")

    # 3. Telegram alert for CFO/LEGAL
    if escalation_level in ("CFO", "LEGAL"):
        try:
            from backend.notifications.telegram_bot import send_escalation_alert
            await send_escalation_alert(record)
        except Exception as e:
            logger.warning(f"[Escalation] Telegram alert failed (non-fatal): {e}")

    logger.info(
        f"[Escalation] {escalation_id} | {agent_type} | {reason_code} | "
        f"confidence={confidence:.2f} threshold={threshold:.2f} | level={escalation_level}"
    )
    return record


def partial_proceed(output: dict, agent_type: str) -> dict:
    """
    For batch outputs where SOME items meet confidence threshold and others don't.
    Proceeds autonomously on high-confidence items.
    Escalates only the low-confidence items.

    Returns:
    {
      "proceed_items": [...],
      "escalate_items": [...],
      "summary": str
    }
    """
    threshold = CONFIDENCE_THRESHOLDS.get(agent_type, 0.75)
    items = output.get("items", [])

    proceed_items = []
    escalate_items = []

    for item in items:
        item_conf = float(item.get("confidence", output.get("confidence", 0.0)))
        if item_conf >= threshold:
            proceed_items.append(item)
        else:
            escalate_items.append({**item, "_escalation_reason": "LOW_CONFIDENCE"})

    total = len(items)
    summary = (
        f"{len(proceed_items)}/{total} items auto-processed "
        f"({len(escalate_items)} escalated for human review) "
        f"[threshold: {threshold:.0%}]"
    )

    return {
        "proceed_items":  proceed_items,
        "escalate_items": escalate_items,
        "summary":        summary,
    }


def format_escalation_message(
    item: dict,
    reason: str,
    agent_type: str,
    confidence: float = 0.0,
    threshold: float = 0.75,
    deadline: Optional[str] = None,
) -> str:
    """
    Formats a human-readable escalation message for dashboard + Telegram.
    """
    reason_text = ESCALATION_REASONS.get(reason, reason)
    conf_pct = f"{confidence*100:.0f}%"
    thresh_pct = f"{threshold*100:.0f}%"

    item_desc = (
        item.get("violation_detail")
        or item.get("description")
        or item.get("narration")
        or item.get("root_cause")
        or json.dumps(item)[:120]
    )
    agent_reasoning = item.get("reasoning", "Agent did not provide detailed reasoning.")
    action_required = item.get("suggested_action", "Please review this item manually and take appropriate action.")
    deadline_line = f"\nDeadline: {deadline}" if deadline else ""

    return (
        f"⚠️ ESCALATION — {agent_type.upper().replace('_', ' ')}\n\n"
        f"Item: {item_desc}\n"
        f"Reason: {reason_text}\n"
        f"Confidence: {conf_pct} (threshold: {thresh_pct})\n"
        f"Agent reasoning: {agent_reasoning}\n\n"
        f"Action required: {action_required}"
        f"{deadline_line}"
    )
