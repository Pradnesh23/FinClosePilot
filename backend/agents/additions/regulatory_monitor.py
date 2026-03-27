"""
Regulatory Change Monitor — watches CBIC and SEBI for new rules.
Runs every 6 hours via background asyncio task.
"""

import logging
import asyncio
from datetime import datetime, timezone
import httpx
from backend.agents.gemini_helper import call_gemini_json
from backend.memory import letta_client as letta
from backend.database.audit_logger import save_regulatory_change
from backend.notifications.telegram_bot import send_guardrail_alert

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a Regulatory Change Monitor for FinClosePilot India.

You will receive raw text from Indian regulatory websites (CBIC, SEBI, MCA).
Extract any NEW rule changes, notifications, or circulars.

For each change found:
1. What regulation changed (GST/SEBI/RBI/IndAS/IncomeTax)
2. What exactly changed (new rule, amendment, clarification)
3. Effective date
4. Which transactions or business areas it affects
5. Action needed by the finance team
6. Urgency: HIGH/MEDIUM/LOW

Return ONLY valid JSON:
{
  "changes_found": [{
    "framework": "GST|SEBI|RBI|IndAS|IncomeTax",
    "notification_no": "string",
    "summary": "string",
    "what_changed": "string",
    "effective_date": "YYYY-MM-DD or null",
    "affected_areas": ["string"],
    "action_required": "string",
    "urgency": "HIGH|MEDIUM|LOW",
    "source_url": "string"
  }],
  "no_changes": bool
}
"""

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FinClosePilot/1.0"
}


async def _fetch_url(url: str) -> str:
    """Async HTTP fetch with timeout and error handling."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=_HEADERS)
            return resp.text[:8000]
    except Exception as e:
        logger.warning(f"[RegMonitor] Fetch failed for {url}: {e}")
        return ""


import hashlib


def _get_page_hash(text: str) -> str:
    """Generate MD5 hash of page content."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _calculate_relevance_score(text: str) -> int:
    """Count occurrences of regulatory keywords."""
    keywords = ["GST", "SEBI", "MCA", "Circular", "Notification", "Amendment", "Rule", "Tax", "IndAS", "RBI"]
    score = sum(1 for kw in keywords if kw.lower() in text.lower())
    return score


async def monitor_cbic() -> dict:
    """Fetch CBIC notifications with hashing and filtering."""
    url = "https://www.cbic.gov.in/htdocs-cbec/gst/"
    raw_text = await _fetch_url(url)

    if not raw_text:
        return {"changes_found": [], "no_changes": True, "source": "CBIC", "error": "fetch_failed"}

    # 1. Deterministic Relevance check
    if _calculate_relevance_score(raw_text) == 0:
        logger.info("[RegMonitor] CBIC: No keywords found, skipping AI.")
        return {"changes_found": [], "no_changes": True, "source": "CBIC"}

    user_msg = f"Source: CBIC GST Notifications page\nURL: {url}\n\nPage content:\n{raw_text[:5000]}"
    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        result["source"] = "CBIC"
        result["page_hash"] = _get_page_hash(raw_text)
        return result
    except Exception as e:
        logger.error(f"[RegMonitor] CBIC extraction failed: {e}")
        return {"changes_found": [], "no_changes": True, "source": "CBIC"}


async def monitor_sebi() -> dict:
    """Fetch SEBI circulars with hashing and filtering."""
    url = "https://www.sebi.gov.in/legal/circulars.html"
    raw_text = await _fetch_url(url)

    if not raw_text:
        return {"changes_found": [], "no_changes": True, "source": "SEBI", "error": "fetch_failed"}

    if _calculate_relevance_score(raw_text) == 0:
        logger.info("[RegMonitor] SEBI: No keywords found, skipping AI.")
        return {"changes_found": [], "no_changes": True, "source": "SEBI"}

    user_msg = f"Source: SEBI Circulars page\nURL: {url}\n\nPage content:\n{raw_text[:5000]}"
    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        result["source"] = "SEBI"
        result["page_hash"] = _get_page_hash(raw_text)
        return result
    except Exception as e:
        logger.error(f"[RegMonitor] SEBI extraction failed: {e}")
        return {"changes_found": [], "no_changes": True, "source": "SEBI"}


async def monitor_mca() -> dict:
    """Fetch MCA notifications with hashing and filtering."""
    url = "https://www.mca.gov.in/content/mca/global/en/acts-rules/ebooks/rules.html"
    raw_text = await _fetch_url(url)

    if not raw_text:
        return {"changes_found": [], "no_changes": True, "source": "MCA", "error": "fetch_failed"}

    if _calculate_relevance_score(raw_text) == 0:
        logger.info("[RegMonitor] MCA: No keywords found, skipping AI.")
        return {"changes_found": [], "no_changes": True, "source": "MCA"}

    user_msg = f"Source: MCA Rules and Notifications page\nURL: {url}\n\nPage content:\n{raw_text[:5000]}"
    try:
        result = await call_gemini_json(SYSTEM_PROMPT, user_msg)
        result["source"] = "MCA"
        result["page_hash"] = _get_page_hash(raw_text)
        return result
    except Exception as e:
        logger.error(f"[RegMonitor] MCA extraction failed: {e}")
        return {"changes_found": [], "no_changes": True, "source": "MCA"}


async def update_guardrail_rules(agent_id: str, letta_client, changes: list) -> None:
    """Process extracted regulatory changes — store to Letta, DB, Telegram."""
    for change in changes:
        # Store to Letta archival
        await letta.store_regulatory_update(letta_client, agent_id, change)

        # Save to SQLite
        save_regulatory_change(change)

        # Send Telegram if HIGH urgency
        if change.get("urgency") == "HIGH":
            await send_guardrail_alert(
                rule_id="REG_UPDATE",
                regulation=f"Regulatory Change — {change.get('framework')}",
                section=change.get("notification_no", "N/A"),
                vendor_name="N/A",
                amount_inr=0,
                violation_detail=change.get("what_changed", "Rule updated"),
                action_taken=change.get("action_required", "Review required"),
                run_id="reg_monitor",
                rule_level="ADVISORY",
            )

        logger.info(f"[RegMonitor] Processed change: {change.get('framework')} — {change.get('summary', '')[:80]}")


async def run_regulatory_monitor(letta_client_, agent_id: str) -> dict:
    """
    Main function — runs all monitors, processes changes, updates memory.
    Called on schedule and on-demand from API.
    """
    logger.info("[RegMonitor] Starting regulatory monitoring cycle...")

    cbic_result = await monitor_cbic()
    sebi_result = await monitor_sebi()
    mca_result = await monitor_mca()

    all_changes = []
    all_changes.extend(cbic_result.get("changes_found", []))
    all_changes.extend(sebi_result.get("changes_found", []))
    all_changes.extend(mca_result.get("changes_found", []))

    if all_changes:
        await update_guardrail_rules(agent_id, letta_client_, all_changes)

    # Update last-check timestamp
    await letta.update_core(letta_client_, agent_id, "last_regulatory_check", {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cbic_checked": not cbic_result.get("error"),
        "sebi_checked": not sebi_result.get("error"),
        "mca_checked": not mca_result.get("error"),
        "changes_found": len(all_changes),
    })

    return {
        "changes_found": len(all_changes),
        "changes": all_changes,
        "cbic_status": "ok" if not cbic_result.get("error") else "error",
        "sebi_status": "ok" if not sebi_result.get("error") else "error",
        "mca_status": "ok" if not mca_result.get("error") else "error",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def start_periodic_regulatory_monitor(letta_client_, agent_id: str) -> None:
    """Background asyncio task — runs every 6 hours. Starts after 30s delay."""
    await asyncio.sleep(30)  # Initial delay on startup
    while True:
        try:
            await run_regulatory_monitor(letta_client_, agent_id)
        except Exception as e:
            logger.error(f"[RegMonitor] Periodic run failed: {e}")
        await asyncio.sleep(6 * 3600)  # 6 hours
