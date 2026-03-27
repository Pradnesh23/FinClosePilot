"""
Statistical Anomaly Detector — Z-Score and IQR.
Detects financial outliers that deviate significantly from historical patterns.
"""

import logging
import json
import numpy as np
from scipy import stats
from backend.agents.gemini_helper import call_gemini_json
from backend.agents.confidence import escalate, CONFIDENCE_THRESHOLDS

logger = logging.getLogger(__name__)


async def _enhance_statistical_with_ai(
    violation: dict,
    vendor_history: list,
) -> dict:
    """Use AI to provide forensic context to a statistical outlier."""
    system_prompt = """
    You are a Forensic Accountant Expert.
    We have detected a statistical outlier (high Z-score or IQR breach).
    
    Your task:
    1. Assess if this outlier is a legitimate business expense or a fraud risk.
    2. Provide a 'forensic_justification'.
    3. Specify the 'risk_profile': 'LOW_BUSINESS_AS_USUAL', 'MEDIUM_UNUSUAL_ACTIVITY', or 'HIGH_FRAUD_INDICATOR'.
    
    Return ONLY valid JSON:
    {
      "risk_profile": "string",
      "forensic_justification": "string",
      "is_legitimate_estimate": bool,
      "confidence_score": float
    }
    """
    
    user_msg = json.dumps({
        "violation": violation,
        "vendor_history_sample": [{k: v for k, v in t.items() if k not in ["letta_id", "id", "transaction_id"]} for t in vendor_history[:10]],
    })
    
    try:
        result = await call_gemini_json(system_prompt, user_msg)
        return result
    except Exception as e:
        logger.error(f"[StatDetector] AI Enhancement failed: {e}")
        return {}

async def detect_statistical_anomalies(
    transactions: list,
    letta_client,
    agent_id: str,
    run_id: str = "demo",
) -> dict:
    """
    Detects outliers using Z-score and IQR methods.
    Returns a list of flagged transactions with reasoning.
    """
    if not transactions:
        return {"violations": [], "summary": "No transactions to analyse."}

    amounts = [float(t.get("amount", 0)) for t in transactions if t.get("amount")]
    if len(amounts) < 10:
        return {"violations": [], "summary": "Insufficient data for statistical analysis (need n >= 10)."}

    data = np.array(amounts)
    
    # ── 1. Z-Score Method (Parametric) ──
    # Good for normally distributed data. Flags > 3 standard deviations.
    z_scores = stats.zscore(data)
    z_flags = np.where(np.abs(z_scores) > 3)[0]
    
    # ── 2. IQR Method (Non-parametric) ──
    # Robust to extreme outliers. Flags > 1.5 * IQR above Q3.
    q1, q3 = np.percentile(data, [25, 75])
    iqr = q3 - q1
    upper_bound = q3 + (1.5 * iqr)
    iqr_flags = np.where(data > upper_bound)[0]
    
    violations = []
    seen_indices = set()
    
    # Combine results
    for idx in set(list(z_flags) + list(iqr_flags)):
        txn = transactions[idx]
        amount = amounts[idx]
        
        reasoning = []
        severity = "MEDIUM"
        
        if idx in z_flags:
            z = abs(z_scores[idx])
            reasoning.append(f"Z-Score {z:.2f} (exceeds 3.0 threshold)")
            if z > 5: severity = "CRITICAL"
            elif z > 4: severity = "HIGH"
            
        if idx in iqr_flags:
            reasoning.append(f"Amount {amount:,} exceeds IQR upper bound ({upper_bound:,.0f})")
            if amount > upper_bound * 2: severity = max(severity, "HIGH")

        violation = {
            "vendor_name": txn.get("vendor_name", "Unknown"),
            "invoice_no": txn.get("invoice_no", "N/A"),
            "amount": amount,
            "anomaly_type": "STATISTICAL_OUTLIER",
            "severity": severity,
            "reasoning": " | ".join(reasoning),
            "method": "Z-Score / IQR Hybrid",
        }
        
        # ── AI ENHANCEMENT ──
        # Use AI to provide forensic context to outliers
        if severity in ["HIGH", "CRITICAL"]:
            vendor_name = txn.get("vendor_name", "Unknown")
            history = [t for t in transactions if (t.get("vendor_canonical") or t.get("vendor_name")) == vendor_name]
            ai_enhancement = await _enhance_statistical_with_ai(violation, history)
            
            if ai_enhancement:
                violation["reasoning"] = f"{violation['reasoning']} | {ai_enhancement.get('forensic_justification')}"
                violation["risk_profile"] = ai_enhancement.get("risk_profile", "MEDIUM")
                violation["ai_confidence"] = ai_enhancement.get("confidence_score", 0.70)
                if ai_enhancement.get("risk_profile") == "LOW_BUSINESS_AS_USUAL":
                    violation["severity"] = "LOW" # Downgrade if AI says it's normal
                    severity = "LOW"

        # Escalate high/critical statistical anomalies
        if severity in ["HIGH", "CRITICAL"]:
            esc = await escalate(
                item=violation,
                reason_code="STAT_OUTLIER_SEV",
                agent_type="anomaly_classification",
                letta_client=letta_client,
                agent_id=agent_id,
                run_id=run_id,
                confidence=violation.get("ai_confidence", 0.90),
                threshold=CONFIDENCE_THRESHOLDS["anomaly_classification"],
                escalation_level="CFO" if severity == "CRITICAL" else "HUMAN_REVIEW",
            )
            violation["escalated"] = True
            
        violations.append(violation)

    return {
        "violations": violations,
        "violation_count": len(violations),
        "mean": float(np.mean(data)),
        "std_dev": float(np.std(data)),
        "upper_bound_iqr": float(upper_bound),
        "summary": (
            f"Analysed {len(amounts)} transactions. "
            f"Found {len(violations)} statistical outliers using Z-score and IQR."
        ),
    }
