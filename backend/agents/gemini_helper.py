"""
Common Gemini helper shared across all agents.
"""

import json
import re
import logging
import google.generativeai as genai
from backend.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)


async def call_gemini(system_prompt: str, user_message: str) -> str:
    full_prompt = f"{system_prompt}\n\nUser: {user_message}"
    response = model.generate_content(full_prompt)
    return response.text


async def call_gemini_json(system_prompt: str, user_message: str) -> dict:
    full_prompt = (
        f"{system_prompt}\n\nUser: {user_message}\n\n"
        "Return ONLY valid JSON. No markdown. No preamble."
    )
    response = model.generate_content(full_prompt)
    text = response.text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        retry_prompt = (
            f"{system_prompt}\n\nUser: {user_message}\n\n"
            "CRITICAL: Return ONLY a raw JSON object. No text before or after. No markdown backticks."
        )
        retry_response = model.generate_content(retry_prompt)
        retry_text = re.sub(r"```[a-z]*\n?", "", retry_response.text).strip()
        try:
            return json.loads(retry_text)
        except json.JSONDecodeError as e:
            logger.error(f"[Gemini] JSON parse failed after retry: {e}")
            return {"error": "json_parse_failed", "raw": retry_text[:500]}
