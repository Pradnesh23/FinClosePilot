"""
Intercompany Reconciliation Agent — Entity-to-entity + IndAS 110.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an Intercompany Reconciliation Agent for FinClosePilot, India.

Reconcile intercompany payables vs receivables across group entities.
Apply IndAS 110 (Consolidated Financial Statements) throughout.

TASKS:
1. Match IC payables (Entity A) vs IC receivables (Entity B)
2. Calculate unrealised profit in inventory per IndAS 110 Para 20:
   unrealised_profit = (ic_profit / ic_revenue) * subsidiary_inventory_at_ic_price
3. Flag uneliminated intercompany balances
4. Check currency differences for foreign subsidiaries (IndAS 21)

Return ONLY strict JSON:
{
  "ic_pairs": [{
    "entity_a": "string",
    "entity_b": "string",
    "payable_amount": float,
    "receivable_amount": float,
    "difference": float,
    "match_status": "MATCHED|MISMATCH|MISSING",
    "regulation": "IndAS 110",
    "elimination_je": "string"
  }],
  "unrealised_profit_eliminations": [{
    "entity_id": "string",
    "ic_profit": float,
    "ic_revenue": float,
    "inventory_at_ic_price": float,
    "unrealised_profit": float,
    "indas_para": "IndAS 110 Para 20"
  }],
  "total_ic_exposure": float,
  "matched_count": int,
  "mismatch_count": int,
  "summary": "string"
}
"""


async def run_intercompany_reconciliation(
    intercompany_data: list,
    letta_client,
    agent_id: str,
) -> dict:
    """Run intercompany reconciliation with IndAS 110 eliminations."""
    user_msg = json.dumps({
        "intercompany_transactions": intercompany_data[:100],
        "count": len(intercompany_data),
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "ic_recon_result",
            "mismatches": result.get("mismatch_count", 0),
            "total_ic": result.get("total_ic_exposure", 0),
        })
        return result
    except Exception as e:
        logger.error(f"[ICRecon] Failed: {e}")
        return {
            "ic_pairs": [], "unrealised_profit_eliminations": [],
            "total_ic_exposure": 0, "matched_count": 0, "mismatch_count": 0,
            "summary": f"IC reconciliation failed: {str(e)}",
        }
