"""
Tax Optimisation Agent — finds legitimate tax saving opportunities.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Tax Optimisation Agent for FinClosePilot India.

Analyse the company's financial data and find LEGITIMATE tax saving opportunities.
Focus on deductions and benefits the company may have missed.

CHECK THESE SPECIFICALLY:

Corporate Tax Deductions:
- Section 80IC/80IE: manufacturing units in special areas (100% deduction)
- Section 35: R&D expenditure (150% deduction available)
- Section 43B: payments to MSME vendors beyond 45 days (disallowance risk)
- Section 40A(3): cash payments above Rs 10,000 (disallowance)

GST Opportunities:
- Input tax credit on capital goods not yet claimed
- Refund of accumulated ITC on exports
- GST paid on advances but later adjusted (refund opportunity)

Income Tax:
- Advance tax instalment shortfall (Section 234C interest risk)
- TDS credit from Form 26AS not matched to books
- Deferred tax asset/liability calculation (IndAS 12)

For each opportunity found:
- Estimated saving in Rs
- Specific section/rule
- Action required
- Deadline if applicable
- Confidence level (0-1)

Return ONLY valid JSON:
{
  "opportunities": [{
    "category": "CorporateTax|GST|IncomeTax",
    "opportunity": "string",
    "regulation": "string",
    "section": "string",
    "estimated_saving_inr": float,
    "action_required": "string",
    "deadline": "YYYY-MM-DD or null",
    "confidence": 0.0-1.0,
    "priority": "HIGH|MEDIUM|LOW"
  }],
  "total_potential_saving_inr": float,
  "executive_summary": "string"
}
"""


async def find_tax_opportunities(
    transactions: list,
    gl_data: list,
    context: dict,
    letta_client,
    agent_id: str,
) -> dict:
    """Find legitimate tax saving opportunities from transaction data."""
    user_msg = json.dumps({
        "transactions_sample": transactions[:100],
        "gl_data_sample": gl_data[:50] if gl_data else [],
        "context": context,
        "total_transactions": len(transactions),
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "tax_opportunities",
            "count": len(result.get("opportunities", [])),
            "total_saving": result.get("total_potential_saving_inr", 0),
        })
        return result
    except Exception as e:
        logger.error(f"[TaxOptimiser] Failed: {e}")
        return {
            "opportunities": [],
            "total_potential_saving_inr": 0,
            "executive_summary": f"Tax analysis failed: {str(e)}",
        }
