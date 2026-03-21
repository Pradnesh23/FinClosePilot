"""
Audit Committee Report Generator — board-level summary.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an Audit Committee Report Generator for FinClosePilot India.

Generate a board-level audit committee report for the close period.
This report will be presented to the Board of Directors and Audit Committee.

Include:
1. EXECUTIVE SUMMARY: Close completion status, key metrics
2. MATERIAL EXCEPTIONS: Only items requiring board attention
3. REGULATORY COMPLIANCE STATUS: GST, SEBI, IndAS — pass/fail per framework
4. ITC BLOCKED: Total amount and reason
5. ANOMALIES ESCALATED: Only CRITICAL and HIGH severity
6. TAX OPTIMISATION HIGHLIGHTS: Top 3 opportunities
7. MANAGEMENT REPRESENTATION: Standard sign-off language
8. ATTESTATION REQUIRED: Items needing CFO/MD signature

Use formal board reporting language. Be concise and precise.
Each section should be ready to paste into board papers.

Return ONLY valid JSON:
{
  "report": {
    "period": "string",
    "generated_at": "ISO8601",
    "executive_summary": "string",
    "close_metrics": {
      "records_processed": int,
      "matched": int,
      "breaks": int,
      "time_taken_minutes": float,
      "automated_resolutions": int
    },
    "material_exceptions": [{
      "exception": "string",
      "amount_inr": float,
      "regulation": "string",
      "action": "string",
      "board_resolution_required": bool
    }],
    "compliance_status": {
      "GST": "COMPLIANT|EXCEPTIONS_NOTED|NON_COMPLIANT",
      "SEBI": "COMPLIANT|EXCEPTIONS_NOTED|NON_COMPLIANT",
      "IndAS": "COMPLIANT|EXCEPTIONS_NOTED|NON_COMPLIANT",
      "IncomeTax": "COMPLIANT|EXCEPTIONS_NOTED|NON_COMPLIANT"
    },
    "itc_summary": {
      "total_blocked_inr": float,
      "reasons": ["string"]
    },
    "top_anomalies": [{
      "type": "string",
      "severity": "string",
      "vendor": "string",
      "amount_inr": float
    }],
    "tax_highlights": ["string"],
    "management_rep_language": "string",
    "attestation_required": ["string"]
  }
}
"""


async def generate_audit_committee_report(
    pipeline_results: dict,
    letta_client,
    agent_id: str,
) -> dict:
    """Generate board-level audit committee report."""
    user_msg = json.dumps({
        "recon_results": pipeline_results.get("recon_results", {}),
        "anomalies": pipeline_results.get("anomalies", {}).get("benford", {}).get("violations", [])[:5],
        "guardrail_results": pipeline_results.get("guardrail_results", {}),
        "tax_opportunities": pipeline_results.get("tax_opportunities", {}).get("opportunities", [])[:5],
        "run_id": pipeline_results.get("run_id"),
        "period": pipeline_results.get("period", "Q3 FY26"),
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "audit_committee_report",
            "period": pipeline_results.get("period"),
        })
        return result
    except Exception as e:
        logger.error(f"[AuditCommittee] Failed: {e}")
        return {"report": {}, "error": str(e)}
