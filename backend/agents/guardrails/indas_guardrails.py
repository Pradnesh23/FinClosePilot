"""
IndAS Compliance Guardrails.
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

SYSTEM_PROMPT = """
You are an IndAS Compliance Guardrail agent for FinClosePilot India.

Check the transactions for IndAS compliance issues.
Apply INDAS_115, INDAS_116, INDAS_110, INDAS_37, INDAS_36.

Return ONLY valid JSON:
{
  "fires": [{
    "rule_id": "string",
    "rule_level": "HARD_BLOCK|SOFT_FLAG|AUTO_ACTION|ADVISORY",
    "regulation": "string",
    "section": "string",
    "vendor_name": "string",
    "transaction_id": "string",
    "amount_inr": float,
    "violation_detail": "string",
    "action_taken": "string"
  }],
  "hard_blocks": int,
  "soft_flags": int,
  "advisories": int,
  "auto_actions": int,
  "summary": "string"
}
"""


async def check_indas_guardrails(
    transactions: list,
    context: dict,
    letta_client,
    agent_id: str,
    run_id: str = "demo",
) -> dict:
    """Run IndAS guardrail checks."""
    user_msg = json.dumps({
        "transactions_sample": transactions[:50],
        "context": context,
        "indas_rules": INDAS_RULES,
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        for fire in result.get("fires", []):
            fire["run_id"] = run_id
            save_guardrail_fire(run_id, fire)
            await letta.store_guardrail_fire(letta_client, agent_id, fire)
        return result
    except Exception as e:
        logger.error(f"[IndASGuardrails] Failed: {e}")
        return {
            "fires": [], "hard_blocks": 0, "soft_flags": 0,
            "advisories": 0, "auto_actions": 0,
            "summary": f"IndAS guardrails failed: {str(e)}",
        }
