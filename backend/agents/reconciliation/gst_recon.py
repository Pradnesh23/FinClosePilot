"""
GST Reconciliation Agent — GSTR-1 vs GSTR-3B vs GSTR-2A vs Books.
"""

import logging
import json
import re
from backend.agents.gemini_helper import call_gemini_json
from backend.agents.model_router import route_call
from backend.agents.confidence import (
    check_confidence, escalate, partial_proceed, CONFIDENCE_THRESHOLDS,
)
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a GST Reconciliation Agent for FinClosePilot, India.

Reconcile GSTR-1 vs GSTR-3B vs GSTR-2A vs Books data.

Root cause classification for each break:
- TIMING_DIFFERENCE: valid period-end timing (auto-clearable)
- ITC_MISMATCH: supplier filing vs company claim discrepancy
- MISSING_BOOKING: transaction exists in one source only
- HSN_MISMATCH: HSN code differs between invoice and return
- RATE_DIFFERENCE: GST rate applied incorrectly
- SUPPLIER_NON_FILING: supplier has not filed GSTR-1
- DUPLICATE_ENTRY: same invoice twice
- CURRENCY_ROUNDING: within 1% tolerance (auto-clearable)

Always check:
- Rule 36(4): ITC cannot exceed GSTR-2A by more than 5%
- Section 16(2): ITC invalid if supplier has not filed

Return ONLY strict JSON. No markdown. No preamble.
Schema:
{
  "total_gstr1": float,
  "total_gstr3b": float,
  "total_gstr2a": float,
  "total_books": float,
  "breaks": [{
    "break_id": "string",
    "vendor_name": "string",
    "vendor_gstin": "string",
    "invoice_no": "string",
    "gstr1_amount": float or null,
    "gstr3b_amount": float or null,
    "gstr2a_amount": float or null,
    "books_amount": float or null,
    "difference": float,
    "root_cause": "string",
    "auto_clearable": bool,
    "regulation": "string",
    "ai_reasoning": "string",
    "confidence": 0.0-1.0
  }],
  "matched_count": int,
  "break_count": int,
  "itc_rule364_violated": bool,
  "itc_section162_issues": ["string"],
  "summary": "string",
  "confidence": 0.0-1.0
}
"""

GSTIN_REGEX = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$")


def _is_valid_gstin(gstin: str) -> bool:
    """Check GSTIN format validity."""
    return bool(gstin and GSTIN_REGEX.match(gstin.strip().upper()))


async def run_gst_reconciliation(
    gstr1: list,
    gstr3b: list,
    gstr2a: list,
    books: list,
    letta_client,
    agent_id: str,
    run_id: str = "demo",
) -> dict:
    """Run full GST reconciliation across all 4 data sources."""
    user_msg = json.dumps({
        "gstr1_sample": gstr1[:50],
        "gstr3b_sample": gstr3b[:50],
        "gstr2a_sample": gstr2a[:50],
        "books_sample": books[:50],
        "gstr1_count": len(gstr1),
        "gstr3b_count": len(gstr3b),
        "gstr2a_count": len(gstr2a),
        "books_count": len(books),
    })

    escalations = []

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)

        # ── Confidence check on overall result ──
        conf_result = check_confidence(result, "reconciliation_root_cause")

        if conf_result["escalation_required"]:
            logger.info(
                f"[GSTRecon] Overall confidence {conf_result['confidence']:.2f} "
                f"below threshold {conf_result['threshold']:.2f} — checking partial proceed"
            )

        # ── Per-break confidence + escalation triggers ──
        proceeded_breaks = []
        escalated_breaks = []
        vendor_break_counts: dict[str, int] = {}

        for brk in result.get("breaks", []):
            brk_confidence = float(brk.get("confidence", conf_result["confidence"]))
            vendor = brk.get("vendor_name", "Unknown")
            gstin = brk.get("vendor_gstin", "")
            amount = float(brk.get("difference", 0))

            # Count breaks per vendor
            vendor_break_counts[vendor] = vendor_break_counts.get(vendor, 0) + 1

            should_escalate = False
            esc_reason = None

            # Trigger 1: Invalid GSTIN + amount > Rs 50,000
            if not _is_valid_gstin(gstin or "") and abs(amount) > 50_000:
                should_escalate = True
                esc_reason = "INVALID_GSTIN_HIGH_AMOUNT"

            # Trigger 2: Same vendor has 3+ breaks
            if vendor_break_counts[vendor] >= 3:
                should_escalate = True
                esc_reason = "REPEATED_BREAKS"

            # Trigger 3: New vendor + amount > Rs 2L (check Letta)
            if not should_escalate and abs(amount) > 2_00_000:
                try:
                    from backend.memory.letta_client import search_memory
                    history = await search_memory(letta_client, agent_id, vendor)
                    if len(history) == 0:
                        should_escalate = True
                        esc_reason = "NEW_VENDOR_HIGH_AMOUNT"
                except Exception:
                    pass

            # Trigger 4: Low confidence on root cause
            threshold = CONFIDENCE_THRESHOLDS["reconciliation_root_cause"]
            if brk_confidence < threshold:
                should_escalate = True
                esc_reason = esc_reason or "LOW_CONFIDENCE"

            if should_escalate:
                esc_record = await escalate(
                    item=brk,
                    reason_code=esc_reason,
                    agent_type="reconciliation_root_cause",
                    letta_client=letta_client,
                    agent_id=agent_id,
                    run_id=run_id,
                    confidence=brk_confidence,
                    threshold=threshold,
                    escalation_level="CFO" if abs(amount) > 5_00_000 else "HUMAN_REVIEW",
                )
                brk["status"] = "ESCALATED"
                brk["escalation_reason"] = esc_reason
                escalated_breaks.append(brk)
                escalations.append(esc_record)
                logger.info(
                    f"[GSTRecon] Break {brk.get('break_id')} escalated — "
                    f"confidence {brk_confidence:.0%} reason={esc_reason}"
                )
            else:
                proceeded_breaks.append(brk)

        # Store summary to Letta archival memory
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "gst_recon_result",
            "breaks": len(result.get("breaks", [])),
            "matched": result.get("matched_count", 0),
            "itc_violation": result.get("itc_rule364_violated", False),
            "escalated": len(escalated_breaks),
            "auto_proceeded": len(proceeded_breaks),
        })

        result["escalations"] = escalations
        result["escalation_summary"] = {
            "total": len(escalations),
            "escalated_breaks": len(escalated_breaks),
            "proceeded_breaks": len(proceeded_breaks),
        }
        return result

    except Exception as e:
        logger.error(f"[GSTRecon] Failed: {e}")
        return {
            "total_gstr1": 0, "total_gstr3b": 0, "total_gstr2a": 0, "total_books": 0,
            "breaks": [], "matched_count": 0, "break_count": 0,
            "itc_rule364_violated": False, "itc_section162_issues": [],
            "summary": f"GST reconciliation failed: {str(e)}",
            "escalations": [],
            "escalation_summary": {"total": 0, "escalated_breaks": 0, "proceeded_breaks": 0},
        }

