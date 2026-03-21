"""
RLAIF Critic Agent — scores agent outputs before they are acted on.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Quality Critic Agent for FinClosePilot.
Score agent outputs on 5 dimensions before they are acted on.

SCORING:
1. reconciliation_accuracy (0-1): Are all break root causes correctly classified?
2. anomaly_precision (0-1): Are anomaly flags plausible given the data?
3. guardrail_citation_quality (0-1): Do all guardrail fires cite exact regulation sections?
4. report_completeness (0-1): Does the report cover all required sections?
5. narrative_accuracy (0-1): Are all AI-generated narratives factually grounded?

THRESHOLDS:
- Overall > 0.85: PROCEED
- 0.70-0.85: FLAG
- < 0.70: RETRY
- guardrail_citation_quality < 0.90: always FLAG regardless of overall score

For each dimension, provide a brief justification of the score.

Return ONLY valid JSON. No markdown.
{
  "scores": {
    "reconciliation_accuracy": float,
    "anomaly_precision": float,
    "guardrail_citation_quality": float,
    "report_completeness": float,
    "narrative_accuracy": float
  },
  "overall_score": float,
  "decision": "PROCEED|FLAG|RETRY",
  "justifications": {
    "reconciliation_accuracy": "string",
    "anomaly_precision": "string",
    "guardrail_citation_quality": "string",
    "report_completeness": "string",
    "narrative_accuracy": "string"
  },
  "critical_issues": ["string"],
  "improvement_suggestions": ["string"]
}
"""


async def critique_output(agent_output: dict, output_type: str) -> dict:
    """Score agent output quality before proceeding."""
    user_msg = json.dumps({
        "output_type": output_type,
        "agent_output_summary": {
            k: v for k, v in agent_output.items()
            if k not in ("raw_data", "transactions", "records")
        },
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        # Ensure decision follows threshold rules
        overall = result.get("overall_score", 0)
        guardrail_cq = result.get("scores", {}).get("guardrail_citation_quality", 1.0)

        if guardrail_cq < 0.90:
            result["decision"] = "FLAG"
        elif overall >= 0.85:
            result["decision"] = "PROCEED"
        elif overall >= 0.70:
            result["decision"] = "FLAG"
        else:
            result["decision"] = "RETRY"

        return result
    except Exception as e:
        logger.error(f"[RLAIFCritic] Failed: {e}")
        return {
            "scores": {
                "reconciliation_accuracy": 0.8,
                "anomaly_precision": 0.8,
                "guardrail_citation_quality": 0.9,
                "report_completeness": 0.8,
                "narrative_accuracy": 0.8,
            },
            "overall_score": 0.82,
            "decision": "FLAG",
            "justifications": {},
            "critical_issues": [f"Critic agent failed: {str(e)}"],
            "improvement_suggestions": [],
        }
