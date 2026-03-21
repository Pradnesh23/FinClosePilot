"""
Multi-Entity Consolidation Agent — IndAS 110 group consolidation.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Multi-Entity Consolidation Agent for FinClosePilot India.

Handle group consolidation for parent company + subsidiaries.
Apply IndAS 110 (Consolidated Financial Statements) throughout.

TASKS:
1. Match intercompany payables (Entity A) vs receivables (Entity B)
2. Calculate unrealised profit in inventory per IndAS 110 Para 20:
   unrealised_profit = (ic_profit / ic_revenue) * subsidiary_inventory_at_ic_price
3. Generate elimination journal entries for each intercompany transaction
4. Identify currency translation adjustments for foreign subsidiaries (IndAS 21)
5. Check minority interest calculations

For each elimination entry provide:
- Dr/Cr accounts
- Amount
- Regulation reference (IndAS 110 Para number)
- Rationale

Return ONLY valid JSON. No markdown.
{
  "elimination_entries": [{
    "entity_a": "string",
    "entity_b": "string",
    "debit_account": "string",
    "credit_account": "string",
    "amount": float,
    "currency": "INR",
    "regulation": "IndAS 110 Para X",
    "rationale": "string",
    "type": "IC_ELIMINATION|PROFIT_ELIMINATION|MINORITY_INTEREST|CURRENCY_TRANSLATION"
  }],
  "group_summary": {
    "total_ic_eliminated": float,
    "unrealised_profit_eliminated": float,
    "minority_interest": float,
    "total_entities": int,
    "entities_complete": int
  },
  "consolidation_adjustments": ["string"],
  "indas_110_commentary": "string"
}
"""


async def run_consolidation(entities: list, letta_client, agent_id: str) -> dict:
    """
    entities: list of {entity_id, entity_name, role: parent|subsidiary,
                       transactions: [], ownership_pct: float}
    """
    user_msg = json.dumps({
        "entities": [
            {
                "entity_id": e.get("entity_id"),
                "entity_name": e.get("entity_name"),
                "role": e.get("role"),
                "ownership_pct": e.get("ownership_pct", 100),
                "transactions_count": len(e.get("transactions", [])),
                "transactions_sample": e.get("transactions", [])[:10],
            }
            for e in entities
        ],
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "consolidation_result",
            "entities": len(entities),
            "eliminations": len(result.get("elimination_entries", [])),
        })
        return result
    except Exception as e:
        logger.error(f"[MultiEntity] run_consolidation failed: {e}")
        return {
            "elimination_entries": [],
            "group_summary": {"total_ic_eliminated": 0, "unrealised_profit_eliminated": 0,
                              "minority_interest": 0, "total_entities": len(entities), "entities_complete": 0},
            "consolidation_adjustments": [f"Consolidation failed: {str(e)}"],
            "indas_110_commentary": "",
        }


async def calculate_intercompany_eliminations(parent_data: dict, subsidiary_data: dict) -> dict:
    """Pure Python calculation of intercompany eliminations per IndAS 110."""
    ic_revenue = float(parent_data.get("ic_revenue", 0))
    ic_profit = float(parent_data.get("ic_profit", 0))
    inventory_at_ic = float(subsidiary_data.get("inventory_at_ic_price", 0))

    if ic_revenue > 0:
        unrealised_profit = (ic_profit / ic_revenue) * inventory_at_ic
    else:
        unrealised_profit = 0

    return {
        "ic_revenue": ic_revenue,
        "ic_profit": ic_profit,
        "ic_profit_margin": ic_profit / ic_revenue if ic_revenue > 0 else 0,
        "inventory_at_ic_price": inventory_at_ic,
        "unrealised_profit": round(unrealised_profit, 2),
        "elimination_je": {
            "dr": "Retained Earnings",
            "cr": "Inventory",
            "amount": round(unrealised_profit, 2),
            "regulation": "IndAS 110 Para 20",
        },
    }


async def get_entity_close_status(entities: list, run_ids: dict) -> dict:
    """Returns close status per entity."""
    from backend.database.models import get_db_connection
    conn = get_db_connection()
    status = {}
    try:
        for entity in entities:
            eid = entity.get("entity_id")
            run_id = run_ids.get(eid)
            if run_id:
                row = conn.execute(
                    "SELECT status, total_records, matched_records FROM pipeline_runs WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
                if row:
                    pct = (row["matched_records"] / max(row["total_records"], 1)) * 100
                    status[eid] = {
                        "status": row["status"],
                        "pct_complete": round(pct, 1),
                        "blocking_items": [],
                    }
                    continue
            status[eid] = {"status": "PENDING", "pct_complete": 0, "blocking_items": []}
    finally:
        conn.close()
    return status
