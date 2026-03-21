"""
Financial Variance Report Generator.
Produces AI-narrated variance analysis for actuals vs budget vs prior period.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Financial Variance Analysis Agent for FinClosePilot.

For each material variance (above 5% or Rs 10 Lakhs):
1. Write a plain English narrative explaining WHY it occurred
2. Reference business events, approvals, decisions from context
3. State if SEBI disclosure is required
4. Reference board resolutions if mentioned in context
5. End with corrective action if variance is unfavourable

Return ONLY valid JSON. No markdown. No preamble.
{
  "variance_items": [{
    "account": "string",
    "actual": float,
    "budget": float,
    "prior_period": float or null,
    "variance_vs_budget": float,
    "variance_vs_budget_pct": float,
    "variance_vs_prior": float or null,
    "variance_vs_prior_pct": float or null,
    "materiality": "MATERIAL|IMMATERIAL",
    "narrative": "string",
    "sebi_disclosure_required": bool,
    "corrective_action": "string or null",
    "board_resolution_ref": "string or null"
  }],
  "total_revenue_variance": float,
  "total_expense_variance": float,
  "executive_summary": "string",
  "sebi_disclosures": ["string"]
}
"""


async def generate_variance_report(
    actuals: dict,
    budget: dict,
    prior_period: dict,
    context: dict,
    letta_client,
    agent_id: str,
) -> dict:
    """Generate AI-narrated variance report."""
    user_msg = json.dumps({
        "actuals": actuals,
        "budget": budget,
        "prior_period": prior_period,
        "context": context,
        "materiality_threshold_inr": 1000000,  # Rs 10 Lakhs
        "materiality_threshold_pct": 5,
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "variance_report",
            "material_variances": len([
                v for v in result.get("variance_items", [])
                if v.get("materiality") == "MATERIAL"
            ]),
        })
        return result
    except Exception as e:
        logger.error(f"[VarianceReport] Failed: {e}")
        return {
            "variance_items": [], "total_revenue_variance": 0,
            "total_expense_variance": 0,
            "executive_summary": f"Variance report failed: {str(e)}",
            "sebi_disclosures": [],
        }
