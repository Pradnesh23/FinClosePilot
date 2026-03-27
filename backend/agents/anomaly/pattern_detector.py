"""
LLM-based pattern anomaly classifier.
Identifies additional patterns like round number clustering, MSME risks, etc.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json # type: ignore
from backend.memory import letta_client as letta # type: ignore

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an Anomaly Pattern Classifier for FinClosePilot, India.

Analyse the list of transactions and identify these specific anomalies:

1. ROUND_NUMBER_CLUSTER: Multiple payments of exact round amounts (e.g. Rs 5,00,000)
   to avoid transaction limits or reporting thresholds.
2. MSME_OVERDUE: Invoices from MSME vendors unpaid beyond 45 days
   (Section 43B disallowance risk — Income Tax Act).
3. YEAR_END_SPIKE: Unusual spike in bookings just before financial year end (March 31)
   that may indicate earnings management.
4. RELATED_PARTY: Transactions with vendors that may be related parties (similar names,
   addresses) not disclosed per SEBI LODR Regulation 23.
5. THRESHOLD_AVOIDANCE: Cash payments just below Rs 10,000 threshold (Section 40A(3)).
6. NON_BUSINESS_HOURS: High-value transactions on weekends or odd hours.

For each anomaly found provide:
- Category from above list
- Severity: CRITICAL|HIGH|MEDIUM|LOW
- Affected vendors/transactions
- Financial exposure in Rs
- Regulation reference
- Recommended action

Return ONLY valid JSON:
{
  "anomalies": [{
    "anomaly_type": "string",
    "severity": "CRITICAL|HIGH|MEDIUM|LOW",
    "vendor_name": "string",
    "vendor_gstin": "string or null",
    "transaction_ids": ["string"],
    "financial_exposure_inr": float,
    "count": int,
    "regulation": "string",
    "reasoning": "string",
    "action_required": "string"
  }],
  "total_exposure_inr": float,
  "summary": "string"
}
"""


async def detect_patterns(
    transactions: list,
    letta_client,
    agent_id: str,
) -> dict:
    """Detect anomaly patterns using Gemini classification."""
    user_msg = json.dumps({
        "transactions": transactions[:200], # type: ignore
        "total_count": len(transactions),
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        for anomaly in result.get("anomalies", []):
            await letta.store_to_archival(letta_client, agent_id, {
                "type": "pattern_anomaly",
                **anomaly,
            })
        return result
    except Exception as e:
        logger.error(f"[PatternDetector] Failed: {e}")
        return {
            "anomalies": [], "total_exposure_inr": 0,
            "summary": f"Pattern detection failed: {str(e)}",
        }
