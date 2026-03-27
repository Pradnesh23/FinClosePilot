"""
Intercompany Reconciliation Agent — Entity-to-entity + IndAS 110/21.
Algorithm-first approach for profit eliminations.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

def _calculate_indas110_eliminations(intercompany_data: list) -> list:
    """Implement IndAS 110 Para 20 math for unrealised profit."""
    eliminations = []
    for item in intercompany_data:
        # Heuristic: only calculate if profit and inventory data is present
        ic_profit = float(item.get("ic_profit", 0))
        ic_revenue = float(item.get("ic_revenue", 0))
        inventory_val = float(item.get("inventory_at_ic_price", 0))
        
        if ic_revenue > 0 and inventory_val > 0:
            unrealised_profit = (ic_profit / ic_revenue) * inventory_val
            eliminations.append({
                "entity_id": item.get("entity_id") or item.get("entity_a") or "Group",
                "ic_profit": ic_profit,
                "ic_revenue": ic_revenue,
                "inventory_at_ic_price": inventory_val,
                "unrealised_profit": round(unrealised_profit, 2),
                "indas_para": "IndAS 110 Para 20"
            })
    return eliminations


async def run_intercompany_reconciliation(
    intercompany_data: list,
    letta_client,
    agent_id: str,
) -> dict:
    """Run intercompany reconciliation with hybrid approach."""
    
    # 1. Deterministic Elimination Logic (IndAS 110)
    eliminations = _calculate_indas110_eliminations(intercompany_data)
    
    # 2. Match IC Pairs (Entity A Payable vs Entity B Receivable)
    ic_pairs = []
    # Simplified matching logic for entities
    for item in intercompany_data:
        p_amt = float(item.get("payable_amount") or item.get("amount", 0))
        r_amt = float(item.get("receivable_amount") or 0)
        
        if r_amt == 0: # If only one side provided in input, we assume the other side exists
            # In a real system, we'd lookup Entity B's books
            pass

        ic_pairs.append({
            "entity_a": item.get("entity_a") or "Entity_A",
            "entity_b": item.get("entity_b") or "Entity_B",
            "payable_amount": p_amt,
            "receivable_amount": r_amt,
            "difference": p_amt - r_amt,
            "match_status": "MATCHED" if abs(p_amt - r_amt) < 1.0 else "MISMATCH",
            "regulation": "IndAS 110",
            "elimination_je": f"Dr {item.get('entity_a')} Payable, Cr {item.get('entity_b')} Receivable"
        })

    # 3. AI Enhancement for Reporting & IndAS 21 (Currency)
    system_prompt = """
    You are an Intercompany Compliance Expert.
    We have matched IC balances and calculated IndAS 110 profit eliminations algorithmically.
    
    Your task:
    1. Verify if the 'eliminations' look mathematically sound.
    2. Check for IndAS 21 (Foreign Currency) implications if entities are in different countries.
    3. Suggest any additional Consolidation Adjustments.
    
    Return ONLY valid JSON:
    {
      "ai_feedback": "string",
      "currency_risks": ["string"],
      "consolidation_summary": "string"
    }
    """
    
    user_msg = json.dumps({
        "matched_pairs_count": len(ic_pairs),
        "eliminations": eliminations,
        "sample_data": intercompany_data[:20]
    })
    
    try:
        ai_res = await call_gemini_json(system_prompt, user_msg)
        summary = ai_res.get("consolidation_summary", f"Reconciled {len(ic_pairs)} intercompany pairs.")
    except Exception as e:
        logger.error(f"[ICRecon] AI check failed: {e}")
        ai_res = {}
        summary = f"Reconciled {len(ic_pairs)} intercompany pairs (Algorithmic)."

    result = {
        "ic_pairs": ic_pairs,
        "unrealised_profit_eliminations": eliminations,
        "total_ic_exposure": sum(p.get("payable_amount", 0) for p in ic_pairs),
        "matched_count": sum(1 for p in ic_pairs if p["match_status"] == "MATCHED"),
        "mismatch_count": sum(1 for p in ic_pairs if p["match_status"] == "MISMATCH"),
        "ai_enhancement": ai_res,
        "summary": summary
    }

    await letta.store_to_archival(letta_client, agent_id, {
        "type": "ic_recon_result",
        "mismatches": result["mismatch_count"],
        "total_ic": result["total_ic_exposure"],
        "eliminations_count": len(eliminations)
    })
    
    return result
