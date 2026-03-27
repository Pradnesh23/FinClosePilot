"""
Benford's Law anomaly analyser.
Uses scipy.stats.chisquare to detect fraudulent transaction patterns.
"""

import logging
import math
import json
import numpy as np # type: ignore
from scipy import stats # type: ignore
from backend.agents.gemini_helper import call_gemini # type: ignore
from backend.agents.model_router import route_call # type: ignore
from backend.agents.confidence import escalate, CONFIDENCE_THRESHOLDS # type: ignore
from backend.memory import letta_client as letta # type: ignore

logger = logging.getLogger(__name__)

# Benford's expected first-digit distribution (%)
BENFORD_EXPECTED = {
    1: 30.1, 2: 17.6, 3: 12.5, 4: 9.7, 5: 7.9,
    6: 6.7, 7: 5.8, 8: 5.1, 9: 4.6,
}


def _get_first_digit(amount: float) -> int | None:
    try:
        s = str(abs(float(amount)))
        for ch in s:
            if ch.isdigit() and ch != "0":
                return int(ch)
    except Exception:
        pass
    return None


def _benford_test(amounts: list[float]) -> dict:
    """Run chi-squared Benford test on a list of amounts."""
    if len(amounts) < 20:
        return {"skip": True, "reason": "insufficient_data", "n": len(amounts)}

    first_digits = [_get_first_digit(a) for a in amounts]
    first_digits = [d for d in first_digits if d is not None]
    n = len(first_digits)
    if n < 20:
        return {"skip": True, "reason": "insufficient_valid_digits", "n": n}

    # Observed counts
    observed = np.array([first_digits.count(d) for d in range(1, 10)], dtype=float)
    expected_counts = np.array([BENFORD_EXPECTED[d] / 100 * n for d in range(1, 10)])

    chi2, p_value = stats.chisquare(observed, expected_counts)

    actual_pct = {d: round(float(observed[d - 1] / n * 100), 1) for d in range(1, 10)} # type: ignore
    expected_pct = {d: BENFORD_EXPECTED[d] for d in range(1, 10)}

    return {
        "skip": False,
        "n": n,
        "chi_square": round(float(chi2), 4), # type: ignore
        "p_value": round(float(p_value), 6), # type: ignore
        "flagged": p_value < 0.05, # type: ignore
        "borderline": 0.05 <= p_value < 0.08, # type: ignore
        "actual_distribution": actual_pct,
        "expected_distribution": expected_pct,
    }


async def _enhance_benford_with_ai(
    violation: dict,
    transactions: list,
    run_id: str,
) -> dict:
    """Use AI to cross-check Benford violation and provide forensic context."""
    from backend.agents.gemini_helper import call_gemini_json
    
    system_prompt = """
    You are a Forensic Accountant Expert assessing a Benford's Law violation.
    
    Your task:
    1. Cross-check the statistical anomaly. Does the distribution variation look like common fraud (e.g., fictitious invoices, threshold evasion)?
    2. Provide a 'forensic_justification' for why this is or isn't suspicious.
    3. Suggest a 'fraud_probability' (0.0 to 1.0).
    4. Categorize the potential fraud type (e.g., 'ROUND_SUM_SCHEME', 'BILL_AND_HOLD', 'BENIGN_SKEW').
    
    Return ONLY valid JSON:
    {
      "ai_confirmation": "CONFIRMED|BENIGN|INSIGHTFUL_CORRECTION",
      "forensic_justification": "string",
      "fraud_probability": float,
      "fraud_type": "string",
      "confidence_score": float
    }
    """
    
    user_msg = json.dumps({
        "vendor_name": violation.get("vendor_name"),
        "actual_distribution": violation.get("actual_distribution"),
        "expected_distribution": violation.get("expected_distribution"),
        "transaction_count": violation.get("transaction_count"),
        "sample_transactions": [{k: v for k, v in t.items() if k not in ["letta_id", "id"]} for t in transactions[:30]],
    })
    
    try:
        result = await call_gemini_json(system_prompt, user_msg)
        return result
    except Exception as e:
        logger.error(f"[Benford] AI Enhancement failed: {e}")
        return {}


async def analyse_benford(
    transactions: list,
    letta_client,
    agent_id: str,
    run_id: str = "demo",
) -> dict:
    """
    Run Benford analysis per vendor.
    Flags vendors where p-value < 0.05 AND transaction_count >= 20.
    """
    # Group by vendor
    vendor_txns: dict[str, list] = {}
    for txn in transactions:
        name = txn.get("vendor_canonical") or txn.get("vendor_name", "Unknown")
        amount = txn.get("amount", 0)
        if amount and float(amount) > 0:
            vendor_txns.setdefault(name, []).append(float(amount))

    violations = []
    all_vendor_results = []
    escalations = []

    for vendor_name, amounts in vendor_txns.items():
        test = _benford_test(amounts)
        test["vendor_name"] = vendor_name

        if test.get("skip"):
            continue

        all_vendor_results.append(test)
        n = test["n"]
        p_value = test["p_value"]
        total_exposure = sum(amounts)

        # ── SMALL SAMPLE ESCALATION (20-30 transactions) ──
        if 20 <= n <= 30:
            esc = await escalate(
                item={
                    "vendor_name": vendor_name,
                    "anomaly_type": "BENFORD_SMALL_SAMPLE",
                    "n": n,
                    "p_value": p_value,
                    "chi_square": test["chi_square"],
                    "financial_exposure_inr": round(total_exposure, 2),
                    "reasoning": (
                        f"Sample size {n} is at minimum threshold. "
                        f"Statistical power is limited. Results are indicative only "
                        f"— manual verification recommended."
                    ),
                },
                reason_code="SMALL_SAMPLE",
                agent_type="anomaly_classification",
                letta_client=letta_client,
                agent_id=agent_id,
                run_id=run_id,
                confidence=0.55,
                threshold=CONFIDENCE_THRESHOLDS["anomaly_classification"],
                escalation_level="HUMAN_REVIEW",
            )
            escalations.append(esc)
            logger.info(
                f"[Benford] Small sample escalation for {vendor_name}: n={n}"
            )

        # ── BORDERLINE P-VALUE ESCALATION (0.05 to 0.08) ──
        if test.get("borderline"):
            esc = await escalate(
                item={
                    "vendor_name": vendor_name,
                    "anomaly_type": "BENFORD_BORDERLINE",
                    "n": n,
                    "p_value": p_value,
                    "chi_square": test["chi_square"],
                    "financial_exposure_inr": round(total_exposure, 2),
                    "reasoning": (
                        f"Benford deviation is near threshold (p={p_value:.4f}). "
                        f"Statistical significance is borderline. "
                        f"Recommend manual review before taking action."
                    ),
                },
                reason_code="BORDERLINE_STATISTIC",
                agent_type="anomaly_classification",
                letta_client=letta_client,
                agent_id=agent_id,
                run_id=run_id,
                confidence=0.65,
                threshold=CONFIDENCE_THRESHOLDS["anomaly_classification"],
                escalation_level="HUMAN_REVIEW",
            )
            escalations.append(esc)
            logger.info(
                f"[Benford] Borderline p-value escalation for {vendor_name}: p={p_value:.4f}"
            )

        if test["flagged"]:
            violation = {
                "vendor_name": vendor_name,
                "anomaly_type": "BENFORD_VIOLATION",
                "severity": "HIGH", # Default, updated below
                "transaction_count": test["n"],
                "chi_square": test["chi_square"],
                "p_value": test["p_value"],
                "financial_exposure_inr": round(total_exposure, 2),
                "actual_distribution": test["actual_distribution"],
                "expected_distribution": test["expected_distribution"],
            }

            # ── AI CROSS-CHECK & ENHANCEMENT ──
            # The user wants to use AI to enhance accuracies of deterministic checks
            relevant_txns = [t for t in transactions if (t.get("vendor_canonical") or t.get("vendor_name")) == vendor_name]
            ai_enhancement = await _enhance_benford_with_ai(violation, relevant_txns, run_id)
            
            if ai_enhancement:
                violation["reasoning"] = ai_enhancement.get("forensic_justification", "Statistical deviation confirmed by forensics.")
                violation["reasoning_confidence"] = ai_enhancement.get("confidence_score", 0.85)
                violation["fraud_probability"] = ai_enhancement.get("fraud_probability", 0.0)
                violation["fraud_type"] = ai_enhancement.get("fraud_type", "UNKNOWN")
                violation["ai_status"] = ai_enhancement.get("ai_confirmation", "CONFIRMED")
            else:
                violation["reasoning"] = "Benford distribution significantly deviates from expected — manual review required."
                violation["reasoning_confidence"] = 0.50

            reasoning_confidence = violation.get("reasoning_confidence", 0.5)
            severity = "CRITICAL" if p_value < 0.01 else "HIGH"
            violation["severity"] = severity

            # ── CRITICAL ANOMALY + LOW LLM REASONING CONFIDENCE ──
            if p_value < 0.001 and reasoning_confidence < 0.80:
                esc = await escalate(
                    item={
                        "vendor_name": vendor_name,
                        "anomaly_type": "BENFORD_CRITICAL_LOW_REASONING",
                        "severity": "CRITICAL",
                        "p_value": p_value,
                        "reasoning_confidence": reasoning_confidence,
                        "financial_exposure_inr": round(total_exposure, 2),
                        "reasoning": (
                            f"High-confidence anomaly (p<0.001) but LLM reasoning confidence "
                            f"is only {reasoning_confidence:.0%}. Manual expert review needed."
                        ),
                    },
                    reason_code="LOW_CONFIDENCE",
                    agent_type="anomaly_classification",
                    letta_client=letta_client,
                    agent_id=agent_id,
                    run_id=run_id,
                    confidence=reasoning_confidence,
                    threshold=CONFIDENCE_THRESHOLDS["anomaly_classification"],
                    escalation_level="CFO",
                )
                escalations.append(esc)

            # violation dict is already built above
            violations.append(violation)

            violations.append(violation)

            # Store to Letta archival
            await letta.store_to_archival(letta_client, agent_id, {
                "type": "benford_violation",
                **violation,
            })

    return {
        "vendors_analysed": len(all_vendor_results),
        "violations": violations,
        "violation_count": len(violations),
        "escalations": escalations,
        "summary": (
            f"Analysed {len(all_vendor_results)} vendors with sufficient data. "
            f"Found {len(violations)} Benford violations. "
            f"{len(escalations)} items escalated."
        ),
    }

