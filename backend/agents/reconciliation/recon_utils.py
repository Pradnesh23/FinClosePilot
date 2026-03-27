"""
Shared Reconciliation Utilities for FinClosePilot.
Deterministic and Fuzzy matching engine.
"""

import logging
from rapidfuzz import process, fuzz, utils

logger = logging.getLogger(__name__)

def fuzzy_match_ledger_data(
    source_a: list, 
    source_b: list, 
    ref_key="invoice_no", 
    amount_key="amount", 
    threshold=90,
    amount_tolerance=1.0
):
    """
    Common reconciliation engine for Books vs GST, Bank vs GL, etc.
    Returns (matched_pairs, unmatched_a, unmatched_b)
    """
    matched = []
    unmatched_a = source_a.copy()
    unmatched_b = source_b.copy()
    
    # 1. Exact Match on (Reference + Amount within tolerance)
    for a in source_a[:]:
        ref_a = str(a.get(ref_key, "")).strip().upper()
        amt_a = float(a.get(amount_key, 0))
        if not ref_a: continue
        
        for b in unmatched_b[:]:
            ref_b = str(b.get(ref_key, "")).strip().upper()
            amt_b = float(b.get(amount_key, 0))
            
            if ref_a == ref_b and abs(amt_a - amt_b) <= amount_tolerance:
                matched.append((a, b))
                if a in unmatched_a: unmatched_a.remove(a)
                unmatched_b.remove(b)
                break
                    
    # 2. Fuzzy Match on Reference + Amount within 1% variance
    for a in unmatched_a[:]:
        ref_a = str(a.get(ref_key, "")).strip().upper()
        if not ref_a: continue
        
        choices = [str(b.get(ref_key, "")).strip().upper() for b in unmatched_b]
        if not choices: break
        
        best_match = process.extractOne(ref_a, choices, scorer=fuzz.ratio, processor=utils.default_process)
        if best_match and best_match[1] >= threshold:
            match_idx = choices.index(best_match[0])
            b = unmatched_b[match_idx]
            amt_a = float(a.get(amount_key, 0))
            amt_b = float(b.get(amount_key, 0))
            
            # Amount tolerance 1% if amount > 0
            is_amt_match = False
            if amt_a != 0:
                if abs(amt_a - amt_b) / abs(amt_a) < 0.01:
                    is_amt_match = True
            elif amt_b == 0:
                is_amt_match = True
                
            if is_amt_match:
                matched.append((a, b))
                unmatched_a.remove(a)
                unmatched_b.remove(b)
                
    return matched, unmatched_a, unmatched_b
