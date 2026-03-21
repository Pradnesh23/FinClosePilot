"""
Vendor AP Ledger vs Vendor Statement of Account (SOA) Reconciliation.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Vendor Reconciliation Agent for FinClosePilot, India.

Reconcile the company's Accounts Payable ledger against vendor Statement of Account (SOA).

Break classification:
- PAYMENT_NOT_ACKNOWLEDGED: company paid but vendor SOA doesn't show
- INVOICE_DISPUTED: amounts differ between ledger and SOA
- CREDIT_NOT_APPLIED: credit note exists in one but not other
- ADVANCE_MISMATCH: advance payment not correctly applied
- TIMING_DIFFERENCE: expected to clear within 7 days
- DEDUCTION_DISPUTE: TDS or other deduction disputed by vendor

For each break:
- Vendor details, invoice references
- Amount difference
- Who is correct (books vs vendor)
- Recommended action

Return ONLY strict JSON:
{
  "vendors_reconciled": int,
  "vendors_with_breaks": int,
  "breaks": [{
    "vendor_name": "string",
    "vendor_gstin": "string",
    "invoice_no": "string",
    "books_amount": float,
    "vendor_soa_amount": float,
    "difference": float,
    "break_type": "string",
    "likely_correct": "BOOKS|VENDOR|UNKNOWN",
    "action_required": "string",
    "auto_clearable": bool
  }],
  "total_disputed_amount": float,
  "summary": "string"
}
"""


async def run_vendor_reconciliation(
    ap_ledger: list,
    vendor_soa: list,
    letta_client,
    agent_id: str,
) -> dict:
    """Run AP ledger vs vendor SOA reconciliation."""
    user_msg = json.dumps({
        "ap_ledger_sample": ap_ledger[:50],
        "vendor_soa_sample": vendor_soa[:50],
        "ap_count": len(ap_ledger),
        "soa_count": len(vendor_soa),
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "vendor_recon_result",
            "vendors_with_breaks": result.get("vendors_with_breaks", 0),
            "disputed_amount": result.get("total_disputed_amount", 0),
        })
        return result
    except Exception as e:
        logger.error(f"[VendorRecon] Failed: {e}")
        return {
            "vendors_reconciled": 0, "vendors_with_breaks": 0,
            "breaks": [], "total_disputed_amount": 0,
            "summary": f"Vendor reconciliation failed: {str(e)}",
        }
