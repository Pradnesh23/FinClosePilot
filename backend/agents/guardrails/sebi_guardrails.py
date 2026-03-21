"""
SEBI LODR Compliance Guardrails.
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

SYSTEM_PROMPT = """
You are a SEBI LODR Compliance Guardrail agent for FinClosePilot India.

Check transactions and context for SEBI LODR violations.
Apply REG_33, REG_23, SCHEDULE_III, REG_29.

REG_23 is critical — any related party transaction exceeding 10% of annual turnover
must generate a HARD_BLOCK requiring shareholder approval.

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
    "action_taken": "string",
    "disclosure_required": bool
  }],
  "hard_blocks": int,
  "soft_flags": int,
  "advisories": int,
  "disclosure_items": ["string"],
  "summary": "string"
}
"""


async def check_sebi_guardrails(
    transactions: list,
    context: dict,
    letta_client,
    agent_id: str,
    run_id: str = "demo",
) -> dict:
    """Run SEBI LODR guardrail checks."""
    user_msg = json.dumps({
        "transactions_sample": transactions[:50],
        "context": context,
        "sebi_rules": SEBI_RULES,
        "quarter_end_date": context.get("quarter_end_date", "2025-12-31"),
        "filing_deadline_days": 45,
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        for fire in result.get("fires", []):
            fire["run_id"] = run_id
            save_guardrail_fire(run_id, fire)
            await letta.store_guardrail_fire(letta_client, agent_id, fire)
        return result
    except Exception as e:
        logger.error(f"[SEBIGuardrails] Failed: {e}")
        return {
            "fires": [], "hard_blocks": 0, "soft_flags": 0, "advisories": 0,
            "disclosure_items": [],
            "summary": f"SEBI guardrails failed: {str(e)}",
        }
