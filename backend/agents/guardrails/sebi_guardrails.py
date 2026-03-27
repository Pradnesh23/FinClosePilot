"""
SEBI LODR Compliance Guardrails.
Algorithm-first approach with AI enhancement.
"""

import logging
import json
from datetime import datetime
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta
from backend.database.audit_logger import save_guardrail_fire

logger = logging.getLogger(__name__)

SEBI_RULES = {
    "REG_33": {
        "description": "Financial results within 45 days of quarter end",
        "level": "SOFT_FLAG",
        "regulation": "SEBI LODR Regulation 33",
        "days_limit": 45,
    },
    "REG_23": {
        "description": "RPT exceeding 10% of turnover needs shareholder approval",
        "level": "HARD_BLOCK",
        "regulation": "SEBI LODR Regulation 23",
        "threshold_pct": 10,
    },
    "SCHEDULE_III": {
        "description": "Specific disclosure format required for listed companies",
        "level": "SOFT_FLAG",
        "regulation": "SEBI LODR Schedule III",
    },
    "REG_29": {
        "description": "Prior intimation of board meetings at least 2 days before",
        "level": "ADVISORY",
        "regulation": "SEBI LODR Regulation 29",
    },
}


def _run_deterministic_sebi_checks(transactions: list, context: dict) -> list:
    """Primary algorithmic checks for SEBI violations."""
    fires = []
    
    # 1. REG_33: Timeline Check
    quarter_end_str = context.get("quarter_end_date", "2025-12-31")
    try:
        quarter_end = datetime.strptime(quarter_end_str, "%Y-%m-%d")
        days_diff = (datetime.now() - quarter_end).days
        if days_diff > 45:
            fires.append({
                "rule_id": "REG_33",
                "rule_level": "SOFT_FLAG",
                "regulation": SEBI_RULES["REG_33"]["regulation"],
                "section": "Financial Reporting",
                "transaction_id": None,
                "amount_inr": 0,
                "violation_detail": f"SEBI Reg 33 deadline exceeded by {days_diff - 45} days.",
                "action_taken": "Flagged for immediate disclosure.",
                "vendor_name": "Entity Compliance"
            })
    except Exception:
        pass

    # 2. REG_23: RPT Threshold Check
    # Assuming turnover is provided in context, else default to a large number
    turnover = float(context.get("annual_turnover", 500_00_00_000))
    rpt_threshold = 0.10 * turnover
    
    for txn in transactions:
        amount = float(txn.get("amount", 0))
        narration = (txn.get("narration") or "").lower()
        
        # Identify Related Party Transactions (heuristic)
        is_rpt = txn.get("is_related_party") or "related party" in narration or "rpt" in narration
        
        if is_rpt and amount > rpt_threshold:
            fires.append({
                "rule_id": "REG_23",
                "rule_level": "HARD_BLOCK",
                "regulation": SEBI_RULES["REG_23"]["regulation"],
                "section": "Related Party Transactions",
                "transaction_id": txn.get("id") or txn.get("transaction_id"),
                "amount_inr": amount,
                "violation_detail": f"RPT of Rs {amount:,.0f} exceeds 10% of annual turnover (Rs {turnover:,.0f}). Requires shareholder approval.",
                "action_taken": "Transaction BLOCKED pending shareholder vote.",
                "vendor_name": txn.get("vendor_canonical") or txn.get("vendor_name")
            })

    return fires


async def _crosscheck_sebi_with_ai(
    transactions: list,
    fires: list,
    context: dict,
    letta_client,
    agent_id: str,
    run_id: str,
) -> list:
    """Use AI to verify SEBI detections and identify disclosure requirements."""
    if not transactions and not fires:
        return fires

    system_prompt = """
    You are a SEBI LODR Compliance Expert.
    1. Verify if the 'fires' (TIMELINE or RPT violations) are correct.
    2. Identify any MISSED violations (e.g., Reg 29 board meeting intimations or Schedule III mapping issues).
    3. Specify exactly which disclosure items are required (e.g., 'Quarterly Results', 'RPT Disclosure').
    
    Return ONLY valid JSON:
    {
      "enhanced_fires": [{
        "rule_id": "string",
        "rule_level": "HARD_BLOCK|SOFT_FLAG|ADVISORY",
        "status": "CONFIRMED|FalsePositive|NEW_DETECTION",
        "disclosure_required": bool,
        "disclosure_type": "string",
        "ai_justification": "string",
        "transaction_id": "string"
      }]
    }
    """
    
    user_msg = json.dumps({
        "context": context,
        "detected_fires": fires,
        "transactions_sample": transactions[:30],
    })
    
    try:
        result = await call_gemini_json(system_prompt, user_msg)
        enhanced_list = []
        ai_fires = result.get("enhanced_fires", [])
        
        for ai_f in ai_fires:
            status = ai_f.get("status")
            if status == "FalsePositive":
                for f in fires:
                    if str(f.get("transaction_id")) == str(ai_f.get("transaction_id")) and f.get("rule_id") == ai_f.get("rule_id"):
                        f["status"] = "REJECTED_BY_AI"
                        f["ai_justification"] = ai_f.get("ai_justification")
            elif status == "NEW_DETECTION":
                txn = next((t for t in transactions if str(t.get("id") or t.get("transaction_id")) == str(ai_f.get("transaction_id"))), {})
                ai_f["run_id"] = run_id
                ai_f["vendor_name"] = txn.get("vendor_canonical") or txn.get("vendor_name")
                ai_f["amount_inr"] = float(txn.get("amount", 0))
                ai_f["source"] = "AI_ENHANCEMENT"
                enhanced_list.append(ai_f)
                save_guardrail_fire(run_id, ai_f)
                await letta.store_guardrail_fire(letta_client, agent_id, ai_f)
            else:
                for f in fires:
                    if str(f.get("transaction_id")) == str(ai_f.get("transaction_id")) and f.get("rule_id") == ai_f.get("rule_id"):
                        f["ai_justification"] = ai_f.get("ai_justification")
                        f["disclosure_required"] = ai_f.get("disclosure_required")
        
        return fires + enhanced_list
    except Exception as e:
        logger.error(f"[SEBIGuardrails] AI Enhancement failed: {e}")
        return fires


async def check_sebi_guardrails(
    transactions: list,
    context: dict,
    letta_client,
    agent_id: str,
    run_id: str = "demo",
) -> dict:
    """Run SEBI LODR guardrail checks using hybrid approach."""
    fires = _run_deterministic_sebi_checks(transactions, context)
    
    enhanced_fires = await _crosscheck_sebi_with_ai(
        transactions, fires, context, letta_client, agent_id, run_id
    )
    
    final_fires = [f for f in enhanced_fires if f.get("status") != "REJECTED_BY_AI"]
    
    hard_blocks = sum(1 for f in final_fires if f.get("rule_level") == "HARD_BLOCK")
    soft_flags = sum(1 for f in final_fires if f.get("rule_level") == "SOFT_FLAG")
    advisories = sum(1 for f in final_fires if f.get("rule_level") == "ADVISORY")

    # Initial logs
    for f in fires:
        f["run_id"] = run_id
        save_guardrail_fire(run_id, f)
        await letta.store_guardrail_fire(letta_client, agent_id, f)

    return {
        "fires": final_fires,
        "hard_blocks": hard_blocks,
        "soft_flags": soft_flags,
        "advisories": advisories,
        "summary": (
            f"SEBI guardrails: {hard_blocks} HARD, {soft_flags} SOFT. AI Enhanced."
        ),
    }
