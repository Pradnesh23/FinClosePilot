"""
Bank Statement vs GL Reconciliation Agent.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Bank Reconciliation Agent for FinClosePilot, India.

Reconcile bank statement entries against the General Ledger (GL).

Break categories:
- TIMING_DIFFERENCE: payment/receipt timing mismatch (within 5 days — auto-clearable)
- MISSING_ENTRY: exists in bank but not in GL (or vice versa)
- AMOUNT_MISMATCH: same reference, different amount
- BANK_CHARGES: bank fee not booked in GL
- BOUNCED_CHEQUE: dishonoured instrument
- INTEREST_CREDIT: bank interest not booked
- UNKNOWN: requires CFO review

For each break:
- Reference number (chq/UTR)
- Bank amount vs GL amount
- Days difference if timing
- Auto-clearable flag
- Recommended journal entry

Return ONLY strict JSON:
{
  "total_bank_debits": float,
  "total_bank_credits": float,
  "total_gl_debits": float,
  "total_gl_credits": float,
  "closing_balance_bank": float,
  "closing_balance_gl": float,
  "breaks": [{
    "break_id": "string",
    "reference_no": "string",
    "break_type": "string",
    "bank_amount": float or null,
    "gl_amount": float or null,
    "difference": float,
    "days_difference": int or null,
    "auto_clearable": bool,
    "description": "string",
    "recommended_je": "string or null"
  }],
  "matched_count": int,
  "break_count": int,
  "summary": "string"
}
"""


from backend.agents.reconciliation.recon_utils import fuzzy_match_ledger_data


async def run_bank_reconciliation(
    bank_statement: list,
    gl_entries: list,
    letta_client,
    agent_id: str,
) -> dict:
    """Run bank vs GL reconciliation using hybrid approach."""
    
    # 1. Deterministic Matching (Reference/Description + Amount)
    matched, bank_rem, gl_rem = fuzzy_match_ledger_data(
        bank_statement, gl_entries, ref_key="description", amount_key="amount"
    )

    user_msg = json.dumps({
        "matched_count": len(matched),
        "bank_unmatched_sample": bank_rem[:30],
        "gl_unmatched_sample": gl_rem[:30],
        "bank_count": len(bank_statement),
        "gl_count": len(gl_entries),
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        
        # Merge deterministic results
        result["matched_count"] = result.get("matched_count", 0) + len(matched)
        
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "bank_recon_result",
            "breaks": len(result.get("breaks", [])),
            "matched": result["matched_count"],
        })
        return result
    except Exception as e:
        logger.error(f"[BankRecon] Failed: {e}")
        return {
            "total_bank_debits": 0, "total_bank_credits": 0,
            "total_gl_debits": 0, "total_gl_credits": 0,
            "closing_balance_bank": 0, "closing_balance_gl": 0,
            "breaks": [], "matched_count": 0, "break_count": 0,
            "summary": f"Bank reconciliation failed: {str(e)}",
        }
