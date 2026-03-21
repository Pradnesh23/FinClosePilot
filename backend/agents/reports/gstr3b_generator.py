"""
GSTR-3B Draft Generator.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a GSTR-3B Draft Generator for FinClosePilot India.

Using the reconciled GST data, generate a complete GSTR-3B draft return.

GSTR-3B has these sections:
3.1 Details of Outward Supplies and Inward Supplies liable to Reverse Charge
3.2 Of the supplies shown in 3.1(a) above, details of inter-State supplies
4. Eligible ITC
5. Values of exempt, nil-rated and non-GST inward supplies
6.1 Payment of tax

Ensure:
- ITC is net of Rule 36(4) adjustments
- Hard-blocked ITC (Section 17(5)) is excluded
- Net tax payable = Output tax - ITC
- Apply any late payment interest (Section 50)

Return ONLY valid JSON:
{
  "gstr3b_draft": {
    "period": "string",
    "gstin": "string",
    "section_3_1": {
      "outward_taxable_igst": float,
      "outward_taxable_cgst": float,
      "outward_taxable_sgst": float,
      "outward_exempt": float,
      "inward_rcm": float,
      "total_outward_tax": float
    },
    "section_4": {
      "itc_igst": float,
      "itc_cgst": float,
      "itc_sgst": float,
      "itc_blocked_17_5": float,
      "itc_rule364_deferred": float,
      "net_itc": float
    },
    "section_6_1": {
      "igst_payable": float,
      "cgst_payable": float,
      "sgst_payable": float,
      "interest_payable": float,
      "total_payable": float
    },
    "filing_notes": ["string"],
    "warnings": ["string"]
  }
}
"""


async def generate_gstr3b(
    recon_results: dict,
    guardrail_results: dict,
    transactions: list,
    letta_client,
    agent_id: str,
    gstin: str = "27AABCX1234D1ZS",
    period: str = "Q3 FY26",
) -> dict:
    """Generate GSTR-3B draft return."""
    user_msg = json.dumps({
        "gst_recon": recon_results.get("gst", {}),
        "guardrail_results": guardrail_results,
        "transactions_sample": transactions[:50],
        "gstin": gstin,
        "period": period,
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "gstr3b_draft",
            "period": period,
            "tax_payable": result.get("gstr3b_draft", {}).get("section_6_1", {}).get("total_payable", 0),
        })
        return result
    except Exception as e:
        logger.error(f"[GSTR3BGenerator] Failed: {e}")
        return {"gstr3b_draft": {}, "error": str(e)}
