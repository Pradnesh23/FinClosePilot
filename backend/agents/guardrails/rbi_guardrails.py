"""
RBI Master Directions Compliance Guardrails.
Algorithm-first approach with AI enhancement.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta
from backend.database.audit_logger import save_guardrail_fire

logger = logging.getLogger(__name__)

RBI_RULES = {
    "FEMA_6": {
        "description": "Foreign payments must have Form 15CA/15CB for amounts > USD 5,000",
        "level": "HARD_BLOCK",
        "regulation": "RBI Master Direction - FEMA 1999 | Income Tax Section 195",
        "threshold_usd": 5000,
    },
    "ECB": {
        "description": "External Commercial Borrowings must follow RBI ECB framework",
        "level": "SOFT_FLAG",
        "regulation": "RBI Master Direction on External Commercial Borrowings 2019",
    },
    "LRS": {
        "description": "LRS limit is USD 250,000 per individual per year",
        "level": "SOFT_FLAG",
        "regulation": "RBI Liberalised Remittance Scheme",
        "annual_limit_usd": 250000,
    },
    "TDS_195": {
        "description": "TDS must be deducted on foreign payments under Section 195",
        "level": "HARD_BLOCK",
        "regulation": "Income Tax Act Section 195 + RBI Guidelines",
    },
}


def _run_deterministic_rbi_checks(transactions: list, context: dict) -> list:
    """Primary algorithmic checks for RBI violations."""
    fires = []
    
    for txn in transactions:
        amount = float(txn.get("amount", 0))
        narration = (txn.get("narration") or "").lower()
        currency = (txn.get("currency") or "INR").upper()
        
        # Heuristic for foreign payment or remittance
        is_foreign = (
            currency != "INR" or 
            any(kw in narration for kw in ["import", "foreign", "remittance", "offshore", "wire transfer", "swift"])
        )
        
        # Simple USD conversion (fixed rate for guardrail heuristic)
        amount_usd = amount / 83.0 if currency == "INR" else amount
        
        # FEMA_6: Foreign remittance > USD 5,000
        if is_foreign and amount_usd > 5000:
            fires.append({
                "rule_id": "FEMA_6",
                "rule_level": "HARD_BLOCK",
                "regulation": RBI_RULES["FEMA_6"]["regulation"],
                "section": "Foreign Remittance (FEMA)",
                "transaction_id": txn.get("id") or txn.get("transaction_id"),
                "amount_inr": amount if currency == "INR" else amount * 83.0,
                "violation_detail": f"Foreign remittance of approx USD {amount_usd:,.0f} detected. Form 15CA/15CB is mandatory.",
                "action_taken": "Transaction BLOCKED pending tax compliance certification.",
                "vendor_name": txn.get("vendor_canonical") or txn.get("vendor_name")
            })

    return fires


async def _crosscheck_rbi_with_ai(
    transactions: list,
    fires: list,
    context: dict,
    letta_client,
    agent_id: str,
    run_id: str,
) -> list:
    """Use AI to verify RBI detections and identify complex ECB/LRS violations."""
    if not transactions and not fires:
        return fires

    system_prompt = """
    You are an RBI Compliance Expert.
    1. Verify if the 'fires' (FEMA/Foreign Payment violations) are correct.
    2. Identify any MISSED violations (e.g., ECB loan repayments, LRS limit breaches, or missing TDS u/s 195).
    3. Look for specifically 'Interest payments' or 'Loan' keywords that suggest ECB framework applies.
    
    Return ONLY valid JSON:
    {
      "enhanced_fires": [{
        "rule_id": "string",
        "rule_level": "HARD_BLOCK|SOFT_FLAG|ADVISORY",
        "status": "CONFIRMED|FalsePositive|NEW_DETECTION",
        "ai_justification": "string",
        "transaction_id": "string",
        "tds_applicable": bool
      }]
    }
    """
    
    user_msg = json.dumps({
        "context": context,
        "detected_fires_count": len(fires),
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
        
        return fires + enhanced_list
    except Exception as e:
        logger.error(f"[RBIGuardrails] AI Enhancement failed: {e}")
        return fires


async def check_rbi_guardrails(
    transactions: list,
    context: dict,
    letta_client,
    agent_id: str,
    run_id: str = "demo",
) -> dict:
    """Run RBI compliance guardrail checks using hybrid approach."""
    fires = _run_deterministic_rbi_checks(transactions, context)
    
    enhanced_fires = await _crosscheck_rbi_with_ai(
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
            f"RBI guardrails: {hard_blocks} HARD, {soft_flags} SOFT. AI Enhanced."
        ),
    }
