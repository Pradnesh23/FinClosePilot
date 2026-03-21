"""
Vendor GSTIN resolver — matches vendor names to canonical GSTINs using fuzzy logic.
"""

import logging
import re
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


def validate_gstin(gstin: str) -> bool:
    """Returns True if GSTIN matches the 15-char format."""
    if not gstin:
        return False
    return bool(GSTIN_PATTERN.match(gstin.strip().upper()))


def resolve_vendor(
    vendor_name: str,
    vendor_gstin: str,
    known_vendors: list[dict],
) -> dict:
    """
    Matches a vendor to canonical records.
    Priority: GSTIN exact match → name fuzzy match.
    Returns {vendor_canonical, merge_confidence, vendor_gstin_validated}.
    """
    gstin_clean = (vendor_gstin or "").strip().upper()
    gstin_valid = validate_gstin(gstin_clean)

    # 1) Exact GSTIN match
    if gstin_valid:
        for kv in known_vendors:
            if kv.get("gstin", "").upper() == gstin_clean:
                return {
                    "vendor_canonical": kv["name"],
                    "merge_confidence": 1.0,
                    "vendor_gstin": gstin_clean,
                    "gstin_valid": True,
                }

    # 2) Fuzzy name match (>= 85%)
    best_score = 0
    best_match = None
    for kv in known_vendors:
        score = fuzz.token_sort_ratio(vendor_name.lower(), kv["name"].lower())
        if score > best_score:
            best_score = score
            best_match = kv

    if best_match and best_score >= 85:
        return {
            "vendor_canonical": best_match["name"],
            "merge_confidence": round(best_score / 100, 2),
            "vendor_gstin": best_match.get("gstin", gstin_clean),
            "gstin_valid": gstin_valid,
        }

    # 3) No match — use raw data
    return {
        "vendor_canonical": vendor_name,
        "merge_confidence": 0.5,
        "vendor_gstin": gstin_clean if gstin_valid else None,
        "gstin_valid": gstin_valid,
    }
