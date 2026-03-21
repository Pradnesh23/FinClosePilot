"""
RBI Master Directions Compliance Guardrails.
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

SYSTEM_PROMPT = """
You are an RBI Compliance Guardrail agent for FinClosePilot India.

Check transactions for RBI Master Direction violations.
Focus on foreign payments, FEMA compliance, ECB, LRS, and TDS on foreign payments.

Return ONLY valid JSON:
{
  "fires": [{
    "rule_id": "string",
    "rule_level": "HARD_BLOCK|SOFT_FLAG|ADVISORY",
    "regulation": "string",
    "section": "string",
    "vendor_name": "string or null",
    "transaction_id": "string or null",
    "amount_inr": float,
    "violation_detail": "string",
    "action_taken": "string"
  }],
  "hard_blocks": int,
  "soft_flags": int,
  "advisories": int,
  "summary": "string"
}
"""


async def check_rbi_guardrails(
    transactions: list,
    context: dict,
    letta_client,
    agent_id: str,
    run_id: str = "demo",
) -> dict:
    """Run RBI compliance guardrail checks."""
    user_msg = json.dumps({
        "transactions_sample": transactions[:50],
        "context": context,
        "rbi_rules": RBI_RULES,
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        for fire in result.get("fires", []):
            fire["run_id"] = run_id
            save_guardrail_fire(run_id, fire)
            await letta.store_guardrail_fire(letta_client, agent_id, fire)
        return result
    except Exception as e:
        logger.error(f"[RBIGuardrails] Failed: {e}")
        return {
            "fires": [], "hard_blocks": 0, "soft_flags": 0, "advisories": 0,
            "summary": f"RBI guardrails failed: {str(e)}",
        }
