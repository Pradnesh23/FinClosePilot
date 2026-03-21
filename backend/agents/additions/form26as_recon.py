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
    """Parse Form 26AS PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        text_pages = []
        for page in doc:
            text_pages.append(page.get_text())
        full_text = "\n".join(text_pages)
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
        }
    except ImportError:
        logger.warning("[Form26AS] PyMuPDF not installed — using text placeholder.")
        return {
            "raw_text": "Form 26AS data (demo mode — PyMuPDF not available)",
            "pages": 1,
            "parts_found": ["part_a", "part_b", "part_c"],
            "parts": {},
        }
    except Exception as e:
        logger.error(f"[Form26AS] PDF parse failed: {e}")
        return {"raw_text": "", "pages": 0, "parts_found": [], "error": str(e)}


async def reconcile_form26as(
    form26as_data: dict,
    books_tds_data: list,
    letta_client,
    agent_id: str,
) -> dict:
    """Run full reconciliation of Form 26AS vs company books."""
    user_msg = json.dumps({
        "form26as_raw": form26as_data.get("raw_text", "")[:3000],
        "form26as_parts": form26as_data.get("parts_found", []),
        "books_tds": books_tds_data[:30],
    })

    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        await letta.store_to_archival(letta_client, agent_id, {
            "type": "form26as_recon",
            "unclaimed_tds": result.get("summary", {}).get("total_tds_unclaimed_inr", 0),
            "notice_risk": result.get("summary", {}).get("estimated_notice_risk"),
        })
        return result
    except Exception as e:
        logger.error(f"[Form26ASRecon] Failed: {e}")
        return {
            "tds_reconciliation": [],
            "advance_tax_reconciliation": {"form26as_total": 0, "books_total": 0, "difference": 0, "status": "UNKNOWN"},
            "summary": {"total_tds_unclaimed_inr": 0, "total_mismatches": 0, "high_risk_items": 0, "estimated_notice_risk": "LOW"},
        }
