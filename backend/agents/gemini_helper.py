"""
Common helper shared across all agents.
In Phase 2, this is now a proxy wrapper around the Tri-Provider `model_router`
so that all legacy agents can use Groq, OpenRouter, or Gemini seamlessly without code changes.
"""

import json
import logging
from backend.agents.model_router import route_call
from backend.config import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

# Basic safety check to ensure at least one key is present
if not any([GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY]):
    logger.warning("No LLM API keys found! Agents will fail.")


async def call_gemini(system_prompt: str, user_message: str) -> str:
    """Legacy method wrapper. Routes to the active provider as a 'flash' tier task."""
    result = await route_call(
        task_type="legacy_general_call",
        system_prompt=system_prompt,
        user_message=user_message,
        run_id="legacy",
        force_json=False
    )
    return result["response"]


async def call_gemini_json(system_prompt: str, user_message: str) -> dict:
    """Legacy method wrapper. Routes to the active provider and parses JSON."""
    result = await route_call(
        task_type="legacy_json_call",
        system_prompt=system_prompt,
        user_message=user_message,
        run_id="legacy",
        force_json=True
    )
    
    text = result["response"].strip()
    
    # Clean up standard markdown formatting
    if text.startswith("```json"): text = text[7:]
    elif text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Retry logic just like the original
        retry_prompt = (
            f"{system_prompt}\n\nUser: {user_message}\n\n"
            "CRITICAL: Return ONLY a raw JSON object. No text before or after. No markdown backticks."
        )
        retry_result = await route_call(
            task_type="legacy_json_retry_call",
            system_prompt="You are a strict JSON formatter.",
            user_message=retry_prompt,
            run_id="legacy_retry",
            force_json=True
        )
        retry_text = retry_result["response"].strip()
        if retry_text.startswith("```json"): retry_text = retry_text[7:]
        elif retry_text.startswith("```"): retry_text = retry_text[3:]
        if retry_text.endswith("```"): retry_text = retry_text[:-3]
        retry_text = retry_text.strip()
        
        try:
            return json.loads(retry_text)
        except json.JSONDecodeError as e:
            logger.error(f"[LLM Proxy] JSON parse failed after retry: {e}")
            return {"error": "json_parse_failed", "raw": retry_text[:500]}


async def call_gemini_vision(system_prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> dict:
    """
    Call Gemini Vision API with an image input for multimodal understanding.
    Used as fallback for complex/scanned PDFs where text extraction fails.
    """
    from google import genai
    from google.genai import types

    if not GEMINI_API_KEY:
        logger.warning("[GeminiVision] No GEMINI_API_KEY — falling back to empty result.")
        return {"error": "no_api_key", "raw_text": ""}

    client = genai.Client(api_key=GEMINI_API_KEY)

    try:
        # Construct multimodal content
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[system_prompt, image_part],
            config=types.GenerateContentConfig(temperature=0.1),
        )

        text = response.text.strip()
        # Try to parse as JSON
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_text": text, "parsed": False}
    except Exception as e:
        logger.error(f"[GeminiVision] API call failed: {e}")
        return {"error": str(e), "raw_text": ""}
