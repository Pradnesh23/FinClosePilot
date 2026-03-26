"""
Statistical Anomaly Detector — Z-Score and IQR.
Detects financial outliers that deviate significantly from historical patterns.
"""

import logging
import numpy as np
from scipy import stats
from backend.agents.confidence import escalate, CONFIDENCE_THRESHOLDS

logger = logging.getLogger(__name__)

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
        
        # Escalate high/critical statistical anomalies
        if severity in ["HIGH", "CRITICAL"]:
            esc = await escalate(
                item=violation,
                reason_code="STAT_OUTLIER_SEV",
                agent_type="anomaly_classification",
                letta_client=letta_client,
                agent_id=agent_id,
                run_id=run_id,
                confidence=0.90,
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
