"""
Fuzzy duplicate payment detector.
Uses rapidfuzz to find duplicate invoices within a 30-day window.
"""

import logging
from datetime import datetime, timedelta
from rapidfuzz import fuzz
from backend.agents.gemini_helper import call_gemini
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 92  # %
WINDOW_DAYS = 30


def _parse_date(date_str: str):
    """Parse date string to datetime."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(str(date_str), fmt)
        except ValueError:
            continue
    return None


def _compute_similarity(txn_a: dict, txn_b: dict) -> float:
    """Weighted similarity on invoice_no, amount, vendor_gstin."""
    inv_score = fuzz.ratio(
        str(txn_a.get("invoice_no", "")), str(txn_b.get("invoice_no", ""))
    )
    amount_a = float(txn_a.get("amount", 0))
    amount_b = float(txn_b.get("amount", 0))
    if amount_a > 0 and amount_b > 0:
        amount_score = 100 if abs(amount_a - amount_b) < 0.01 else max(
            0, 100 - abs(amount_a - amount_b) / max(amount_a, amount_b) * 100
        )
    else:
        amount_score = 0
    gstin_a = str(txn_a.get("vendor_gstin", ""))
    gstin_b = str(txn_b.get("vendor_gstin", ""))
    gstin_score = 100 if gstin_a == gstin_b and gstin_a else 0
    return 0.4 * inv_score + 0.4 * amount_score + 0.2 * gstin_score


async def detect_duplicates(
    transactions: list,
    letta_client,
    agent_id: str,
) -> dict:
    """
    Detect fuzzy duplicate payments within 30-day window.
    Returns duplicates with weighted similarity > 92%.
    """
    duplicates = []
    seen_pairs = set()

    for i, txn_a in enumerate(transactions):
        date_a = _parse_date(txn_a.get("date", ""))
        if not date_a:
            continue
        for j, txn_b in enumerate(transactions):
            if i >= j:
                continue
            pair_key = (min(i, j), max(i, j))
            if pair_key in seen_pairs:
                continue
            date_b = _parse_date(txn_b.get("date", ""))
            if not date_b:
                continue
            if abs((date_a - date_b).days) > WINDOW_DAYS:
                continue

            similarity = _compute_similarity(txn_a, txn_b)
            if similarity >= SIMILARITY_THRESHOLD:
                seen_pairs.add(pair_key)
                # Get Gemini reasoning
                reason_prompt = (
                    f"Transaction A: Invoice {txn_a.get('invoice_no')} | "
                    f"Vendor {txn_a.get('vendor_name')} | Amount Rs {txn_a.get('amount')} | Date {txn_a.get('date')}\n"
                    f"Transaction B: Invoice {txn_b.get('invoice_no')} | "
                    f"Vendor {txn_b.get('vendor_name')} | Amount Rs {txn_b.get('amount')} | Date {txn_b.get('date')}\n"
                    f"Similarity score: {similarity:.1f}%\n\n"
                    "Is this a likely duplicate payment? Explain in 2 sentences and state the financial risk."
                )
                try:
                    reasoning = await call_gemini(
                        "You are a forensic accounting expert.",
                        reason_prompt,
                    )
                except Exception:
                    reasoning = f"High similarity ({similarity:.1f}%) detected — possible duplicate payment."

                dup = {
                    "anomaly_type": "DUPLICATE_PAYMENT",
                    "severity": "HIGH",
                    "transaction_id_a": txn_a.get("transaction_id", f"txn_{i}"),
                    "transaction_id_b": txn_b.get("transaction_id", f"txn_{j}"),
                    "vendor_name": txn_a.get("vendor_name", "Unknown"),
                    "vendor_gstin": txn_a.get("vendor_gstin"),
                    "invoice_no": txn_a.get("invoice_no"),
                    "amount": float(txn_a.get("amount", 0)),
                    "financial_exposure_inr": float(txn_a.get("amount", 0)),
                    "date_a": str(txn_a.get("date")),
                    "date_b": str(txn_b.get("date")),
                    "days_apart": abs((date_a - date_b).days),
                    "similarity_score": round(similarity, 1),
                    "reasoning": reasoning,
                }

                duplicates.append(dup)

                await letta.store_to_archival(letta_client, agent_id, {
                    "type": "duplicate_detected",
                    **dup,
                })

    return {
        "duplicates": duplicates,
        "duplicate_count": len(duplicates),
        "total_exposure_inr": sum(d["financial_exposure_inr"] for d in duplicates),
        "summary": f"Detected {len(duplicates)} potential duplicate payments.",
    }
