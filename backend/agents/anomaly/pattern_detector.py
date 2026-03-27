"""
Pattern Anomaly Detector — Deterministic Heuristics + AI Enhancement.
Identifies round numbers, MSME risks, threshold avoidance, etc.
"""

import logging
import json
from datetime import datetime
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

def _parse_date(date_str: str):
    """Parse date string to datetime."""
    if not date_str: return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(str(date_str), fmt)
        except ValueError:
            continue
    return None

def _run_deterministic_patterns(transactions: list) -> list:
    """Run algorithmic pattern detection heuristics."""
    anomalies = []
    
    for txn in transactions:
        amount = float(txn.get("amount", 0))
        narration = (txn.get("narration") or "").lower()
        txn_id = txn.get("id") or txn.get("transaction_id")
        vendor = txn.get("vendor_name") or "Unknown"

        # 1. ROUND_NUMBER_CLUSTER
        if amount >= 10000 and amount % 1000 == 0:
            anomalies.append({
                "anomaly_type": "ROUND_NUMBER_CLUSTER",
                "severity": "MEDIUM",
                "vendor_name": vendor,
                "transaction_ids": [txn_id],
                "financial_exposure_inr": amount,
                "regulation": "General Audit Principles",
                "reasoning": f"Exact round amount Rs {amount:,.0f} detected. Possible simplified billing or threshold evasion."
            })

        # 2. THRESHOLD_AVOIDANCE (Section 40A(3) - Rs 10,000)
        if 9500 <= amount < 10000:
            anomalies.append({
                "anomaly_type": "THRESHOLD_AVOIDANCE",
                "severity": "HIGH",
                "vendor_name": vendor,
                "transaction_ids": [txn_id],
                "financial_exposure_inr": amount,
                "regulation": "Income Tax Act Section 40A(3)",
                "reasoning": f"Amount Rs {amount:,.0f} is suspiciously close to the Rs 10,000 cash payment limit."
            })

        # 3. NON_BUSINESS_HOURS (Weekends)
        dt = _parse_date(txn.get("date"))
        if dt and dt.weekday() >= 5:
            anomalies.append({
                "anomaly_type": "NON_BUSINESS_HOURS",
                "severity": "LOW",
                "vendor_name": vendor,
                "transaction_ids": [txn_id],
                "financial_exposure_inr": amount,
                "regulation": "Internal Control Standards",
                "reasoning": f"Transaction processed on {dt.strftime('%A')}. Unusual for business operations."
            })

    return anomalies


async def _enhance_patterns_with_ai(
    transactions: list,
    detected_anomalies: list,
    agent_id: str,
    letta_client,
) -> dict:
    """Use AI to discover complex patterns and verify deterministic flags."""
    system_prompt = """
    You are a Forensic Accounting Expert specializing in Indian corporate patterns.
    We have used algorithms to detect round numbers and threshold avoidance.
    
    Your task:
    1. Verify the 'detected_anomalies'. Are they genuine risks or benign (e.g., standard monthly rent)?
    2. Discover NEW patterns:
       - YEAR_END_SPIKE: Are there unusual high-value bookings in late March?
       - MSME_OVERDUE: Do any transactions suggest overdue payments (>45 days) to MSMEs?
       - RELATED_PARTY: Do any vendors look like undisclosed related parties?
    
    Return ONLY valid JSON:
    {
      "enhanced_anomalies": [{
        "anomaly_type": "string",
        "severity": "CRITICAL|HIGH|MEDIUM|LOW",
        "vendor_name": "string",
        "transaction_ids": ["string"],
        "financial_exposure_inr": float,
        "regulation": "string",
        "reasoning": "string",
        "status": "CONFIRMED|FalsePositive|NEW_DETECTION"
      }],
      "summary": "string"
    }
    """
    
    user_msg = json.dumps({
        "detected_anomalies": detected_anomalies,
        "transactions_sample": [{k: v for k, v in t.items() if k not in ["letta_id", "id"]} for t in transactions[:40]],
    })
    
    try:
        result = await call_gemini_json(system_prompt, user_msg)
        return result
    except Exception as e:
        logger.error(f"[PatternDetector] AI Enhancement failed: {e}")
        return {"enhanced_anomalies": [], "summary": "AI enhancement failed."}


async def detect_patterns(
    transactions: list,
    letta_client,
    agent_id: str,
) -> dict:
    """Detect anomaly patterns using hybrid approach."""
    # 1. Deterministic Heuristics
    initial_anomalies = _run_deterministic_patterns(transactions)
    
    # 2. AI Enhancement
    ai_result = await _enhance_patterns_with_ai(transactions, initial_anomalies, agent_id, letta_client)
    
    final_anomalies = []
    enhanced = ai_result.get("enhanced_anomalies", [])
    
    # Process AI results
    for e in enhanced:
        status = e.get("status")
        if status == "FalsePositive":
            # Filter from initial if it matches
            initial_anomalies = [a for a in initial_anomalies if not (a["anomaly_type"] == e["anomaly_type"] and a["vendor_name"] == e["vendor_name"])]
        elif status == "NEW_DETECTION":
            final_anomalies.append(e)
        else:
            # CONFIRMED or existing
            for a in initial_anomalies:
                if a["anomaly_type"] == e["anomaly_type"] and a["vendor_name"] == e["vendor_name"]:
                    a["reasoning"] = e.get("reasoning", a["reasoning"])
                    a["severity"] = e.get("severity", a["severity"])
    
    final_anomalies.extend(initial_anomalies)
    
    for anomaly in final_anomalies:
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "pattern_anomaly",
            **anomaly,
        })
        
    return {
        "anomalies": final_anomalies,
        "total_exposure_inr": sum(a.get("financial_exposure_inr", 0) for a in final_anomalies),
        "summary": ai_result.get("summary", f"Detected {len(final_anomalies)} patterns using hybrid engine.")
    }
