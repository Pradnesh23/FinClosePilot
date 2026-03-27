"""
Form 26AS / AIS Reconciliation Agent.
"""

import logging
import json
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Form 26AS/AIS Reconciliation Agent for FinClosePilot India.

Form 26AS is the Annual Information Statement from the Income Tax department.
It contains: TDS deducted by payers, advance tax paid, tax refunds, high-value transactions.

AIS (Annual Information Statement) has additional data:
interest received, dividends, mutual fund transactions, foreign remittances.

RECONCILIATION TASKS:
1. Match TDS entries in Form 26AS against TDS receivable in company books
2. Flag any TDS not claimed as credit in the tax computation
3. Match advance tax payments against books
4. Flag mismatches that could trigger income tax notices
5. Identify high-value transactions in AIS not reflected in books

For each mismatch:
- Type: TDS_UNCLAIMED|TDS_MISMATCH|ADVANCE_TAX_DIFF|AIS_MISMATCH
- Amount difference in Rs
- Risk: HIGH (could trigger notice) | MEDIUM | LOW
- Action: what to do to resolve

Return ONLY valid JSON:
{
  "tds_reconciliation": [{
    "deductor_name": "string",
    "deductor_tan": "string",
    "form26as_amount": float,
    "books_amount": float,
    "difference": float,
    "mismatch_type": "string",
    "risk": "HIGH|MEDIUM|LOW",
    "action_required": "string"
  }],
  "advance_tax_reconciliation": {
    "form26as_total": float,
    "books_total": float,
    "difference": float,
    "status": "MATCHED|MISMATCH"
  },
  "summary": {
    "total_tds_unclaimed_inr": float,
    "total_mismatches": int,
    "high_risk_items": int,
    "estimated_notice_risk": "HIGH|MEDIUM|LOW"
  }
}
"""


async def parse_form26as_pdf(pdf_path: str) -> dict:
    """Parse Form 26AS PDF using PyMuPDF. Falls back to Gemini Vision for scanned/image PDFs."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        text_pages = []
        for page in doc:
            text_pages.append(page.get_text())
        full_text = "\n".join(text_pages)

        # If text extraction yielded very little content, this is likely a scanned/image PDF
        # Fall back to Gemini Vision for OCR + understanding
        if len(full_text.strip()) < 100:
            logger.info("[Form26AS] Sparse text detected — trying Gemini Vision fallback...")
            try:
                from backend.agents.gemini_helper import call_gemini_vision

                # Convert first page (or all pages up to 3) to images
                vision_results = []
                for i, page in enumerate(doc):
                    if i >= 3:  # Limit to 3 pages for cost
                        break
                    pix = page.get_pixmap(dpi=200)
                    img_bytes = pix.tobytes("png")

                    vision_prompt = (
                        "Extract ALL data from this Form 26AS page. "
                        "Include: Part A (TDS on salary), Part B (TDS on other income), Part C (Advance tax). "
                        "For each entry extract: deductor name, TAN, amount, date. "
                        "Return as JSON with keys: entries (list of {deductor, tan, amount, date, section}), "
                        "page_number, part_type."
                    )
                    result = await call_gemini_vision(vision_prompt, img_bytes, "image/png")
                    vision_results.append(result)

                # Combine vision results into text
                combined_text = json.dumps(vision_results, indent=2)
                doc.close()

                return {
                    "raw_text": combined_text[:5000],
                    "pages": len(text_pages),
                    "parts_found": ["part_a", "part_b", "part_c"],
                    "parts": {"vision_extracted": True},
                    "extraction_method": "gemini_vision",
                    "vision_data": vision_results,
                }
            except Exception as ve:
                logger.warning(f"[Form26AS] Gemini Vision fallback failed: {ve}")
                # Continue with sparse text below

        doc.close()

        # Extract key sections using text patterns
        parts = {}
        if "Part A" in full_text or "PART A" in full_text:
            parts["part_a"] = "TDS on salary entries found"
        if "Part B" in full_text or "PART B" in full_text:
            parts["part_b"] = "TDS on other income entries found"
        if "Part C" in full_text or "PART C" in full_text:
            parts["part_c"] = "Advance tax entries found"

        return {
            "raw_text": full_text[:5000],
            "pages": len(text_pages),
            "parts_found": list(parts.keys()),
            "parts": parts,
            "extraction_method": "pymupdf_text",
        }
    except ImportError:
        logger.warning("[Form26AS] PyMuPDF not installed — using text placeholder.")
        return {
            "raw_text": "Form 26AS data (demo mode — PyMuPDF not available)",
            "pages": 1,
            "parts_found": ["part_a", "part_b", "part_c"],
            "parts": {},
            "extraction_method": "placeholder",
        }
    except Exception as e:
        logger.error(f"[Form26AS] PDF parse failed: {e}")
        return {"raw_text": "", "pages": 0, "parts_found": [], "error": str(e)}


from backend.agents.reconciliation.recon_utils import fuzzy_match_ledger_data


async def reconcile_form26as(
    form26as_data: dict,
    books_tds_data: list,
    letta_client,
    agent_id: str,
) -> dict:
    """Run full reconciliation of Form 26AS vs company books using hybrid approach."""
    
    raw_text = form26as_data.get("raw_text", "")
    
    # 1. Deterministic Extraction (Heuristic)
    # In a real system, we'd use regex to build structured entries from raw_text.
    # For now, we simulate the extraction of a few entries for matching.
    extracted_entries = []
    # (Regex simulation: looking for patterns like TAN: [A-Z]{4}\d{5}[A-Z] and amounts)
    import re
    tan_pattern = re.compile(r"([A-Z]{4}\d{5}[A-Z])")
    amt_pattern = re.compile(r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)")
    
    tans = tan_pattern.findall(raw_text)
    amts = amt_pattern.findall(raw_text)
    
    for i in range(min(len(tans), len(amts))):
        extracted_entries.append({
            "deductor_tan": tans[i],
            "amount": float(amts[i].replace(",", "")),
            "source": "Form26AS"
        })

    # 2. Deterministic Match (TAN + Amount)
    matched, form_rem, books_rem = fuzzy_match_ledger_data(
        extracted_entries, books_tds_data, ref_key="deductor_tan", amount_key="amount"
    )

    user_msg = json.dumps({
        "matched_deterministic_count": len(matched),
        "form26as_unmatched_sample": form_rem[:20],
        "books_unmatched_sample": books_rem[:20],
        "raw_text_snippet": raw_text[:2000],
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        
        # Merge deterministic matches into the result
        result["summary"]["total_mismatches"] = len(result.get("tds_reconciliation", []))
        # (Matched items aren't listed in 'tds_reconciliation' as they are not mismatches)
        
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "form26as_recon",
            "unclaimed_tds": result.get("summary", {}).get("total_tds_unclaimed_inr", 0),
            "notice_risk": result.get("summary", {}).get("estimated_notice_risk"),
            "matched_count": len(matched)
        })
        return result
    except Exception as e:
        logger.error(f"[Form26ASRecon] Failed: {e}")
        return {
            "tds_reconciliation": [],
            "advance_tax_reconciliation": {"form26as_total": 0, "books_total": 0, "difference": 0, "status": "UNKNOWN"},
            "summary": {"total_tds_unclaimed_inr": 0, "total_mismatches": 0, "high_risk_items": 0, "estimated_notice_risk": "LOW"},
        }
