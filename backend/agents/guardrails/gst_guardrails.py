"""
GST Compliance Guardrails — CGST Act 2017 rules.
Hard blocks and soft flags on transactions.
"""

import logging
import json
from datetime import datetime
from backend.agents.gemini_helper import call_gemini_json # type: ignore
from backend.agents.confidence import escalate, check_confidence # type: ignore
from backend.memory import letta_client as letta # type: ignore
from backend.database.audit_logger import save_guardrail_fire # type: ignore

logger = logging.getLogger(__name__)

# Union territory state codes with special GST provisions
UT_STATE_CODES = {"26", "35", "38"}  # D&N Haveli, Andaman, Ladakh

GST_RULES = {
    "S16_2": {
        "description": "ITC valid only if supplier filed GSTR-1 return",
        "level": "SOFT_FLAG",
        "regulation": "CGST Act 2017 Section 16(2)",
    },
    "S17_5_B_I": {
        "description": "No ITC on food, beverages, outdoor catering, entertainment, beauty",
        "level": "HARD_BLOCK",
        "regulation": "CGST Act 2017 Section 17(5)(b)(i)",
        "blocked_keywords": [
            "food", "beverage", "catering", "entertainment", "hospitality",
            "beauty", "restaurant", "hotel food", "party", "celebration",
            "outdoor catering", "club",
        ],
    },
    "S17_5_B_II": {
        "description": "No ITC on health services, cosmetic surgery, club membership",
        "level": "HARD_BLOCK",
        "regulation": "CGST Act 2017 Section 17(5)(b)(ii)",
        "blocked_keywords": [
            "health service", "medical", "gym", "club membership",
            "cosmetic", "surgery", "spa", "wellness",
        ],
    },
    "RULE_36_4": {
        "description": "ITC cannot exceed GSTR-2A by more than 5%",
        "level": "SOFT_FLAG",
        "regulation": "CGST Act 2017 Rule 36(4)",
        "threshold_percent": 5,
    },
    "S34": {
        "description": "Credit notes for rate changes must be within same financial year",
        "level": "ADVISORY",
        "regulation": "CGST Act 2017 Section 34",
    },
    "S50": {
        "description": "Interest at 18% per annum on delayed GST payment",
        "level": "SOFT_FLAG",
        "regulation": "CGST Act 2017 Section 50",
        "interest_rate": 18,
    },
}


def _check_s17_5(txn: dict) -> dict | None:
    """Check Section 17(5) blocked ITC categories."""
    narration = (txn.get("narration_clean") or txn.get("narration") or "").lower()
    vendor = (txn.get("vendor_canonical") or txn.get("vendor_name") or "").lower()

    for rule_id, rule in [("S17_5_B_I", GST_RULES["S17_5_B_I"]), ("S17_5_B_II", GST_RULES["S17_5_B_II"])]:
        for keyword in rule["blocked_keywords"]: # type: ignore
            if keyword in narration or keyword in vendor: # type: ignore
                itc = (
                    float(txn.get("cgst") or 0)
                    + float(txn.get("sgst") or 0)
                    + float(txn.get("igst") or 0)
                )
                if itc > 0:
                    return {
                        "rule_id": rule_id,
                        "rule_level": "HARD_BLOCK",
                        "regulation": rule["regulation"], # type: ignore
                        "section": rule_id.replace("_", " "),
                        "vendor_name": txn.get("vendor_canonical") or txn.get("vendor_name"),
                        "vendor_gstin": txn.get("vendor_gstin"),
                        "transaction_id": txn.get("id") or txn.get("transaction_id"),
                        "amount_inr": float(txn.get("amount", 0)),
                        "itc_blocked_inr": itc,
                        "violation_detail": f"ITC Rs {itc:,.0f} blocked — keyword '{keyword}' matches rule",
                        "action_taken": "ITC reversed. Transaction flagged for CA review.",
                        "matched_keyword": keyword,
                    }
    return None


def _check_rule364(books_itc: float, gstr2a_itc: float) -> dict | None:
    """Check Rule 36(4) — ITC cannot exceed GSTR-2A by more than 5%."""
    if gstr2a_itc <= 0:
        return None
    excess_pct = ((books_itc - gstr2a_itc) / gstr2a_itc) * 100
    if excess_pct > 5:
        return {
            "rule_id": "RULE_36_4",
            "rule_level": "SOFT_FLAG",
            "regulation": GST_RULES["RULE_36_4"]["regulation"],
            "section": "Rule 36(4)",
            "books_itc": books_itc,
            "gstr2a_itc": gstr2a_itc,
            "excess_pct": round(excess_pct, 2), # type: ignore
            "excess_amount": round(books_itc - gstr2a_itc, 2), # type: ignore
            "violation_detail": f"ITC claimed Rs {books_itc:,.0f} exceeds GSTR-2A Rs {gstr2a_itc:,.0f} by {excess_pct:.1f}%",
            "action_taken": "Excess ITC queued for next quarter (deferred).",
        }
    return None


def _check_jurisdiction(txn: dict) -> dict | None:
    """Check for union territory special GST jurisdictions."""
    gstin = txn.get("vendor_gstin") or ""
    amount = float(txn.get("amount", 0))
    if len(gstin) >= 2 and gstin[:2] in UT_STATE_CODES and amount > 1_00_000:
        return {
            "rule_id": "UT_JURISDICTION",
            "rule_level": "ADVISORY",
            "regulation": "UTGST/CGST Special Provisions",
            "section": f"State Code {gstin[:2]}",
            "vendor_name": txn.get("vendor_canonical") or txn.get("vendor_name"),
            "vendor_gstin": gstin,
            "transaction_id": txn.get("id") or txn.get("transaction_id"),
            "amount_inr": amount,
            "violation_detail": f"Special GST jurisdiction (state code {gstin[:2]}). Verify applicable rate structure.",
            "action_taken": "Flagged for jurisdiction review.",
        }
    return None


async def check_gst_guardrails(
    transactions: list,
    recon_results: dict,
    letta_client,
    agent_id: str,
    run_id: str = "demo",
) -> dict:
    """Run all GST guardrail checks on transactions."""
    fires = []
    hard_blocks = 0
    soft_flags = 0
    advisories = 0
    total_blocked_inr = 0
    total_flagged_inr = 0
    escalations = []

    # Track per-transaction fires for conflict detection
    txn_fires: dict[str, list] = {}

    # Check each transaction for S17(5) violations + jurisdiction
    for txn in transactions:
        txn_id = str(txn.get("id") or txn.get("transaction_id", "unknown"))
        txn_fire_list: list[dict] = []

        # S17(5) hard block check
        fire = _check_s17_5(txn)
        if fire:
            txn_fire_list.append(fire)

        # Jurisdiction check (UT state codes)
        jur_fire = _check_jurisdiction(txn)
        if jur_fire:
            txn_fire_list.append(jur_fire)
            # Escalate jurisdiction issues
            esc = await escalate(
                item=jur_fire,
                reason_code="JURISDICTION_UNKNOWN",
                agent_type="guardrail_enforcement",
                letta_client=letta_client,
                agent_id=agent_id,
                run_id=run_id,
                confidence=0.60,
                threshold=0.90,
                escalation_level="HUMAN_REVIEW",
            )
            escalations.append(esc)

        # ── CONFLICTING RULE DETECTION ──
        # If a transaction triggers BOTH HARD_BLOCK and SOFT_FLAG → escalate
        levels_hit = set(f.get("rule_level") for f in txn_fire_list)
        if "HARD_BLOCK" in levels_hit and len(levels_hit) > 1:
            logger.warning(
                f"[GSTGuardrails] Conflicting guardrails on txn {txn_id}: "
                f"{[f.get('rule_id') for f in txn_fire_list]}"
            )
            # DO NOT apply either automatically
            conflict_item = {
                "transaction_id": txn_id,
                "vendor_name": txn.get("vendor_canonical") or txn.get("vendor_name"),
                "amount_inr": float(txn.get("amount", 0)),
                "conflicting_rules": [f.get("rule_id") for f in txn_fire_list],
                "violation_detail": (
                    f"Conflicting guardrails: {' vs '.join(f.get('rule_id', '?') for f in txn_fire_list)}. "
                    f"Neither applied automatically."
                ),
                "reasoning": "Two rules with conflicting levels fire on the same transaction.",
            }
            esc = await escalate(
                item=conflict_item,
                reason_code="CONFLICTING_RULES",
                agent_type="guardrail_enforcement",
                letta_client=letta_client,
                agent_id=agent_id,
                run_id=run_id,
                confidence=0.50,
                threshold=0.90,
                escalation_level="LEGAL",
            )
            escalations.append(esc)
            # Still record the fires for audit trail but mark them ESCALATED
            for f in txn_fire_list:
                f["status"] = "ESCALATED_CONFLICT"
                f["run_id"] = run_id
                fires.append(f)
                save_guardrail_fire(run_id, f)
        else:
            # Normal flow: apply fires
            for fire in txn_fire_list:
                fire["run_id"] = run_id
                fires.append(fire)
                if fire.get("rule_level") == "HARD_BLOCK":
                    hard_blocks += 1 # type: ignore
                    total_blocked_inr += float(fire.get("itc_blocked_inr") or fire.get("amount_inr") or 0) # type: ignore
                elif fire.get("rule_level") == "SOFT_FLAG":
                    soft_flags += 1 # type: ignore
                    total_flagged_inr += float(fire.get("amount_inr") or 0) # type: ignore
                else:
                    advisories += 1 # type: ignore
                save_guardrail_fire(run_id, fire)
                await letta.store_guardrail_fire(letta_client, agent_id, fire)

    # Check Rule 36(4) from recon results
    gst_recon = recon_results.get("gst", {})
    if gst_recon.get("itc_rule364_violated"):
        books_itc = gst_recon.get("total_books", 0)
        gstr2a_itc = gst_recon.get("total_gstr2a", 0)
        fire = _check_rule364(books_itc, gstr2a_itc)
        if fire:
            fire["run_id"] = run_id
            fire["vendor_name"] = "Multiple vendors"
            fire["vendor_gstin"] = None
            fire["transaction_id"] = None
            fire["amount_inr"] = fire.get("excess_amount", 0)
            fires.append(fire)
            soft_flags += 1 # type: ignore
            total_flagged_inr += float(fire.get("excess_amount") or 0) # type: ignore
            save_guardrail_fire(run_id, fire)
            await letta.store_guardrail_fire(letta_client, agent_id, fire)

    return {
        "fires": fires,
        "hard_blocks": hard_blocks,
        "soft_flags": soft_flags,
        "advisories": advisories,
        "total_blocked_inr": round(total_blocked_inr, 2),
        "total_flagged_inr": round(total_flagged_inr, 2), # type: ignore
        "rules_applied": list(GST_RULES.keys()),
        "escalations": escalations,
        "summary": (
            f"GST guardrails: {hard_blocks} HARD BLOCKs, "
            f"{soft_flags} SOFT FLAGs, {advisories} ADVISORY. "
            f"{len(escalations)} escalated."
        ),
    }

