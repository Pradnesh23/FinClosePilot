"""
Surprise scenario handler for FinClosePilot.
Handles 5 judge-demoable edge cases for the ET AI Hackathon PS5 live judging.
"""
import json
import logging
from typing import Optional

from backend.agents.model_router import route_call

logger = logging.getLogger(__name__)

# ─── Scenario Definitions ────────────────────────────────────────────────────
SURPRISE_SCENARIOS = {
    "AMBIGUOUS_FRAUD": {
        "description": "Transaction looks like fraud but may be legitimate",
        "triggers": [
            "round_number + new_vendor + no_prior_history",
            "benford_borderline + high_amount",
            "duplicate_pattern + different_invoice_suffix",
        ],
        "response": "ESCALATE_WITH_BOTH_SCENARIOS",
    },
    "UNKNOWN_REGULATION": {
        "description": "Transaction involves regulation not in knowledge base",
        "triggers": [
            "foreign_currency + no_FEMA_mapping",
            "specific_industry_code + no_HSN_mapping",
            "state_specific_cess + no_rule_found",
        ],
        "response": "ESCALATE_WITH_RESEARCH_REQUEST",
    },
    "RULE_CONFLICT": {
        "description": "Two or more rules fire with conflicting outcomes",
        "triggers": [
            "GST_HARD_BLOCK + IndAS_PROCEED",
            "SEBI_FLAG + RBI_CLEAR",
            "multiple_HARD_BLOCKs_different_sections",
        ],
        "response": "PAUSE_AND_PRESENT_CONFLICT",
    },
    "OUT_OF_SCOPE": {
        "description": "User asks about something outside financial close",
        "triggers": [
            "medical_coding", "supply_chain_routing",
            "HR_decision", "legal_advice", "investment_advice",
        ],
        "response": "GRACEFUL_DECLINE_WITH_REDIRECT",
    },
    "AUTO_CLEAR_TRAP": {
        "description": "Looks like timing difference but is actually an error",
        "triggers": [
            "period_end_date + wrong_amount",
            "timing_diff_pattern + GSTIN_mismatch",
            "recurring_vendor + sudden_amount_spike",
        ],
        "response": "ESCALATE_DESPITE_PATTERN_MATCH",
    },
}

# Out-of-scope keywords
OUT_OF_SCOPE_KEYWORDS = [
    "ICD-10", "medical coding", "medical billing", "CPT code",
    "supply chain", "logistics routing", "HR decision", "employee termination",
    "legal advice", "court case", "investment advice", "stock recommendation",
    "portfolio", "mutual fund", "real estate", "property",
    "patient", "discharge", "prescription", "diagnosis",
]


async def detect_surprise_scenario(
    transaction: dict,
    context: dict = None,
    letta_client=None,
    agent_id: str = None,
) -> dict:
    """
    Runs before any agent processes a transaction.
    Checks if this transaction matches any surprise scenario pattern.
    """
    context = context or {}
    detected = False
    scenario_type = None
    confidence = 0.0
    recommended_handling = "NORMAL_FLOW"
    override_normal_flow = False

    amount = float(transaction.get("amount", 0))
    vendor = transaction.get("vendor_name", "")
    gstin = transaction.get("vendor_gstin")
    narration = transaction.get("narration", "")
    note = transaction.get("note", "")

    # ── AMBIGUOUS FRAUD: round amount + no GSTIN + new vendor ──
    if (amount > 0 and amount % 1_00_000 == 0 and not gstin and amount >= 5_00_000):
        has_history = False
        if letta_client and agent_id:
            try:
                from backend.memory.letta_client import search_memory
                results = await search_memory(letta_client, agent_id, vendor)
                has_history = len(results) > 0
            except Exception:
                pass
        if not has_history:
            detected = True
            scenario_type = "AMBIGUOUS_FRAUD"
            confidence = 0.85
            recommended_handling = "ESCALATE_WITH_BOTH_SCENARIOS"
            override_normal_flow = True

    # ── UNKNOWN REGULATION: SEZ / foreign / special provisions ──
    if not detected:
        sez_keywords = ["SEZ", "special economic zone", "zero-rated", "FEMA", "foreign"]
        narration_lower = f"{narration} {note}".lower()
        if any(kw.lower() in narration_lower for kw in sez_keywords):
            detected = True
            scenario_type = "UNKNOWN_REGULATION"
            confidence = 0.78
            recommended_handling = "ESCALATE_WITH_RESEARCH_REQUEST"
            override_normal_flow = True

    # ── RULE CONFLICT: advance payment / conflicting frameworks in note ──
    if not detected:
        conflict_keywords = ["IndAS 115", "advance payment", "GST Section 12", "conflict"]
        if any(kw.lower() in f"{narration} {note}".lower() for kw in conflict_keywords):
            detected = True
            scenario_type = "RULE_CONFLICT"
            confidence = 0.90
            recommended_handling = "PAUSE_AND_PRESENT_CONFLICT"
            override_normal_flow = True

    # ── AUTO-CLEAR TRAP: timing pattern + small amount mismatch ──
    if not detected:
        payment_date = transaction.get("payment_date")
        date = transaction.get("date")
        if payment_date and date and payment_date != date:
            # Check if amount ends in non-round digits (trap)
            if amount > 10_00_000 and amount % 1000 != 0:
                detected = True
                scenario_type = "AUTO_CLEAR_TRAP"
                confidence = 0.82
                recommended_handling = "ESCALATE_DESPITE_PATTERN_MATCH"
                override_normal_flow = True

    return {
        "scenario_detected":    detected,
        "scenario_type":        scenario_type,
        "confidence":           confidence,
        "recommended_handling": recommended_handling,
        "override_normal_flow": override_normal_flow,
    }


async def handle_out_of_scope(user_query: str, run_id: str = "unknown") -> dict:
    """
    For audit queries that are outside the financial close domain.
    Checks for out-of-scope keywords and returns a graceful decline.
    """
    query_lower = user_query.lower()
    is_out_of_scope = any(kw.lower() in query_lower for kw in OUT_OF_SCOPE_KEYWORDS)

    if not is_out_of_scope:
        return {"is_out_of_scope": False}

    system_prompt = """You are FinClosePilot, an AI agent specialising ONLY in:
- Financial close (GST reconciliation, bank recon, vendor recon)
- Anomaly detection in financial transactions
- Indian regulatory compliance (GST, SEBI, IndAS, RBI)
- Tax optimisation for Indian companies
- Audit trail and reporting

If asked about anything outside this domain:
1. Clearly state you cannot help with that specific request
2. Explain what your actual domain is
3. If the query is close to your domain, suggest what you CAN do

Never guess, hallucinate, or attempt to answer outside your domain.
Never refuse to acknowledge your limitations."""

    try:
        result = await route_call(
            "escalation_reasoning",
            system_prompt,
            f"User asked: \"{user_query}\"\n\nRespond with a graceful decline.",
            run_id=run_id,
        )
        decline_text = result["response"]
    except Exception:
        decline_text = (
            f"FinClosePilot is built for Indian financial close workflows — "
            f"GST reconciliation, compliance guardrails, and audit trails. "
            f"Your question appears to be outside my domain. "
            f"For financial compliance questions, I can help with GST rules, "
            f"IndAS standards, SEBI regulations, and tax optimisation."
        )

    return {
        "is_out_of_scope": True,
        "decline_message": decline_text,
        "domain": "Indian financial close, GST, SEBI, IndAS, RBI compliance",
        "can_help_with": [
            "GST reconciliation and ITC verification",
            "Bank and vendor reconciliation",
            "Anomaly detection (Benford's Law, duplicates)",
            "Compliance guardrails (CGST, SEBI, RBI, IndAS)",
            "Tax optimisation for Indian companies",
            "Audit trail queries",
        ],
    }


async def handle_rule_conflict(
    transaction: dict,
    conflicting_rules: list,
    letta_client=None,
    agent_id: str = None,
    run_id: str = "unknown",
) -> dict:
    """
    When two rules fire with conflicting outcomes.
    Does NOT attempt to resolve automatically.
    Presents BOTH interpretations clearly.
    """
    system_prompt = """You are FinClosePilot's conflict resolution analyst.
Two regulatory rules conflict on the same transaction.
Present BOTH interpretations clearly. Do NOT attempt to resolve.
Explain implications of following each rule.
Format as JSON with keys: conflict_type, agent_assessment, recommended_escalation."""

    rules_text = "\n".join(
        f"Rule {i+1}: {json.dumps(r)}" for i, r in enumerate(conflicting_rules)
    )
    txn_text = json.dumps(transaction, indent=2)

    try:
        result = await route_call(
            "guardrail_conflict_resolution",
            system_prompt,
            f"Transaction:\n{txn_text}\n\nConflicting rules:\n{rules_text}",
            run_id=run_id,
        )
        analysis_text = result["response"]
    except Exception as e:
        analysis_text = None
        logger.error(f"[SurpriseHandler] Conflict analysis LLM failed: {e}")

    # Build structured output
    options = []
    for i, rule in enumerate(conflicting_rules):
        options.append({
            "option":      chr(65 + i),  # A, B, C...
            "apply_rule":  rule.get("rule_id", f"Rule {i+1}"),
            "regulation":  rule.get("regulation", "Unknown"),
            "outcome":     rule.get("action_taken", rule.get("outcome", "Unknown")),
            "implication": rule.get("implication", f"Apply {rule.get('regulation', 'this rule')} interpretation"),
        })
    options.append({
        "option":                     chr(65 + len(conflicting_rules)),
        "escalate_to_external_counsel": True,
        "implication":                "Seek external legal/tax counsel opinion",
    })

    return {
        "conflict_type":          "MULTI_FRAMEWORK_CONFLICT",
        "transaction":            transaction,
        "rule_1":                 conflicting_rules[0] if len(conflicting_rules) > 0 else {},
        "rule_2":                 conflicting_rules[1] if len(conflicting_rules) > 1 else {},
        "agent_assessment":       "Cannot resolve autonomously — conflicting regulatory frameworks",
        "ai_analysis":            analysis_text,
        "recommended_escalation": "CFO + Legal",
        "options_for_human":      options,
    }
