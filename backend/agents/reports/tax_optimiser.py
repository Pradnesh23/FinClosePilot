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

- Section 80JJAA: employment of new employees (30% deduction)
- Section 43B: MSME payments (Section 43B(h) - 2024 amendment)
- Section 35: R&D expenditure (150% deduction available)
- Section 40A(3): cash payments above Rs 10,000 (disallowance)

GST Opportunities & Rules:
- Rule 36(4): 5% provisional ITC on mismatched invoices
- Rule 86B: 99% limit on utilizing ITC for high-turnover companies
- Rule 42/43: Reversal of ITC for exempt supplies or personal use
- Input tax credit on capital goods not yet claimed
- Refund of accumulated ITC on exports (LUT vs. IGST pay)
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
        "transactions_sample": transactions[:150],
        "gl_data_sample": gl_data[:50] if gl_data else [],
        "context": {
            **context,
            "itc_available_in_books": sum(float(t.get("cgst", 0) + t.get("sgst", 0) + t.get("igst", 0)) for t in transactions),
            "tax_laws_applied": ["Rule 36(4)", "Rule 86B", "Section 43B(h)", "Section 80JJAA"]
        },
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
