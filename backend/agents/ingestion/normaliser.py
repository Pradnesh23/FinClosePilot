"""
Data Normalisation Agent.
Normalises raw financial data into clean standardised JSON using Gemini.
"""

import logging
from backend.agents.gemini_helper import call_gemini_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Financial Data Normalisation Agent for FinClosePilot,
India's AI-native financial close system.

Normalise raw financial data into clean standardised JSON.

RULES:
- Dates: convert to YYYY-MM-DD
- Amounts: INR numeric, no commas or symbols
- GSTIN: validate 15-character alphanumeric format, flag invalids
- Vendor names: use GSTIN as primary match key. If GSTIN matches: confidence 1.0.
  If name similarity > 85% and city matches: confidence 0.87.
- Remove duplicate headers, merged cells, empty rows

OUTPUT: Strict JSON only. No preamble. No markdown backticks.
Schema:
{
  "source": "GST_PORTAL|BANK|ERP|VENDOR_INVOICE",
  "records": [{
    "id": "string",
    "date": "YYYY-MM-DD",
    "vendor_gstin": "string or null",
    "vendor_canonical": "string",
    "merge_confidence": 0.0-1.0,
    "amount": float,
    "type": "DEBIT|CREDIT",
    "reference_no": "string or null",
    "narration_clean": "string",
    "gst_rate": float or null,
    "hsn_code": "string or null",
    "igst": float or null,
    "cgst": float or null,
    "sgst": float or null,
    "source_raw": "string"
  }],
  "normalisation_notes": ["string"]
}
"""


async def normalise_data(raw_text: str, source_type: str) -> dict:
    """
    Normalise raw financial data via Gemini.
    Returns a dict matching the normalisation schema.
    """
    user_msg = f"Source type: {source_type}\n\nRaw data (first 8000 chars):\n{raw_text[:8000]}"
    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        if "records" not in result:
            result["records"] = []
        if "normalisation_notes" not in result:
            result["normalisation_notes"] = []
        result["source"] = source_type
        return result
    except Exception as e:
        logger.error(f"[Normaliser] Failed: {e}")
        return {
            "source": source_type,
            "records": [],
            "normalisation_notes": [f"Normalisation failed: {str(e)}"],
        }
