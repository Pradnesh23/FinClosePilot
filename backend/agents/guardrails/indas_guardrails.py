"""
IndAS Compliance Guardrails.
Algorithm-first approach with AI enhancement.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta
from backend.database.audit_logger import save_guardrail_fire

logger = logging.getLogger(__name__)

INDAS_RULES = {
    "INDAS_115": {
        "description": "Revenue only after performance obligation met",
        "level": "HARD_BLOCK",
        "regulation": "IndAS 115 - Revenue from Contracts with Customers",
    },
    "INDAS_116": {
        "description": "Leases must be assessed for ROU asset recognition",
        "level": "SOFT_FLAG",
        "regulation": "IndAS 116 - Leases",
    },
    "INDAS_110": {
        "description": "Intercompany profit in inventory must be eliminated",
        "level": "AUTO_ACTION",
        "regulation": "IndAS 110 Para 20 - Consolidated Financial Statements",
        "formula": "unrealised_profit = (ic_profit / ic_revenue) * inventory_at_cost",
    },
    "INDAS_37": {
        "description": "Probable contingent obligations must be provisioned",
        "level": "SOFT_FLAG",
        "regulation": "IndAS 37 - Provisions, Contingent Liabilities",
    },
    "INDAS_36": {
        "description": "Impairment trigger events must be assessed and documented",
        "level": "ADVISORY",
        "regulation": "IndAS 36 - Impairment of Assets",
    },
}


def _run_deterministic_checks(transactions: list) -> list:
    """Primary algorithmic checks for IndAS violations."""
    fires = []
    
    # INDAS_116 (Leases) Keywords
    lease_kws = ["lease", "rent", "office rent", "warehouse rent", "right of use", "rou asset"]
    # INDAS_37 (Provisions) Keywords
    prov_kws = ["provision", "contingent", "legal fee", "litigation", "court", "penalty", "dispute"]
    # INDAS_36 (Impairment) Keywords
    imp_kws = ["impairment", "write down", "obsolescence", "technical failure", "stopped production"]

    for txn in transactions:
        txn_id = txn.get("id") or txn.get("transaction_id")
        narration = (txn.get("narration") or "").lower()
        amount = float(txn.get("amount", 0))
        
        # Check INDAS_116
        for kw in lease_kws:
            if kw in narration:
                fires.append({
                    "rule_id": "INDAS_116",
                    "rule_level": "SOFT_FLAG",
                    "regulation": INDAS_RULES["INDAS_116"]["regulation"],
                    "section": "Lease Assessment",
                    "transaction_id": txn_id,
                    "amount_inr": amount,
                    "violation_detail": f"Keyword '{kw}' suggests a lease. Verify ROU asset recognition under IndAS 116.",
                    "action_taken": "Flagged for lease accounting review.",
                    "vendor_name": txn.get("vendor_canonical") or txn.get("vendor_name")
                })
                break

        # Check INDAS_37
        for kw in prov_kws:
            if kw in narration:
                fires.append({
                    "rule_id": "INDAS_37",
                    "rule_level": "SOFT_FLAG",
                    "regulation": INDAS_RULES["INDAS_37"]["regulation"],
                    "section": "Provisions",
                    "transaction_id": txn_id,
                    "amount_inr": amount,
                    "violation_detail": f"Trigger keyword '{kw}' found. Assess if a provision or contingent liability disclosure is needed.",
                    "action_taken": "Flagged for IndAS 37 legal/finance review.",
                    "vendor_name": txn.get("vendor_canonical") or txn.get("vendor_name")
                })
                break

        # Check INDAS_36
        for kw in imp_kws:
            if kw in narration:
                fires.append({
                    "rule_id": "INDAS_36",
                    "rule_level": "ADVISORY",
                    "regulation": INDAS_RULES["INDAS_36"]["regulation"],
                    "section": "Impairment Trigger",
                    "transaction_id": txn_id,
                    "amount_inr": amount,
                    "violation_detail": f"Impairment trigger '{kw}' detected. Documentation of impairment test required.",
                    "action_taken": "Added to impairment assessment tracker.",
                    "vendor_name": txn.get("vendor_canonical") or txn.get("vendor_name")
                })
                break

    return fires


async def _crosscheck_indas_with_ai(
    transactions: list,
    fires: list,
    context: dict,
    letta_client,
    agent_id: str,
    run_id: str,
) -> list:
    """Use AI to enhance IndAS detections, especially for complex rules like INDAS 115."""
    if not transactions and not fires:
        return fires

    system_prompt = """
    You are an IndAS Compliance Expert. We use deterministic algorithms for basic checks, but we need your expertise for:
    1. IndAS 115 (Revenue Recognition): Look for 'Advance from customer' or revenue recognized without clear delivery proof.
    2. Nuanced Detections: Identify any IndAS 116 or 37 issues that the simple keyword filter missed.
    3. Verification: Verify if the existing 'fires' are correct.
    
    Return ONLY valid JSON:
    {
      "enhanced_fires": [{
        "rule_id": "string",
        "rule_level": "HARD_BLOCK|SOFT_FLAG|ADVISORY",
        "regulation": "string",
        "transaction_id": "string",
        "violation_detail": "string",
        "ai_confidence": float,
        "ai_justification": "string",
        "status": "CONFIRMED|FalsePositive|NEW_DETECTION"
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
                        f["ai_confidence"] = ai_f.get("ai_confidence")
                        f["ai_justification"] = ai_f.get("ai_justification")
        
        return fires + enhanced_list
    except Exception as e:
        logger.error(f"[IndASGuardrails] AI Enhancement failed: {e}")
        return fires


async def check_indas_guardrails(
    transactions: list,
    context: dict,
    letta_client,
    agent_id: str,
    run_id: str = "demo",
) -> dict:
    """Run IndAS guardrail checks using hybrid approach."""
    # 1. Deterministic Checks
    fires = _run_deterministic_checks(transactions)
    
    # 2. AI Enhancement
    enhanced_fires = await _crosscheck_indas_with_ai(
        transactions, fires, context, letta_client, agent_id, run_id
    )
    
    # 3. Finalization
    final_fires = [f for f in enhanced_fires if f.get("status") != "REJECTED_BY_AI"]
    
    hard_blocks = sum(1 for f in final_fires if f.get("rule_level") == "HARD_BLOCK")
    soft_flags = sum(1 for f in final_fires if f.get("rule_level") == "SOFT_FLAG")
    advisories = sum(1 for f in final_fires if f.get("rule_level") == "ADVISORY")
    auto_actions = sum(1 for f in final_fires if f.get("rule_level") == "AUTO_ACTION")

    # Log initial deterministic fires (AI enhancement logs its own)
    for f in fires:
        f["run_id"] = run_id
        save_guardrail_fire(run_id, f)
        await letta.store_guardrail_fire(letta_client, agent_id, f)

    return {
        "fires": final_fires,
        "hard_blocks": hard_blocks,
        "soft_flags": soft_flags,
        "advisories": advisories,
        "auto_actions": auto_actions,
        "summary": (
            f"IndAS guardrails: {hard_blocks} HARD, {soft_flags} SOFT, "
            f"{auto_actions} AUTO. AI Enhanced."
        ),
    }
