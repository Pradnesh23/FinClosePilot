"""
Telegram CFO Alert notifications for FinClosePilot.
Sends real-time alerts on guardrail fires, anomalies, and pipeline completion.
"""

import logging
import asyncio
from typing import Optional

from backend.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CFO_CHAT_ID

logger = logging.getLogger(__name__)

# Guard: only initialise if tokens are set
_bot_available = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CFO_CHAT_ID)
_application = None


def _format_inr(amount: float) -> str:
    """Format amount in Indian numbering style."""
    try:
        amount = int(amount)
        s = str(amount)
        if len(s) <= 3:
            return s
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        return ",".join(parts) + "," + last3
    except Exception:
        return str(amount)


def _level_emoji(rule_level: str) -> str:
    mapping = {"HARD_BLOCK": "⛔", "SOFT_FLAG": "⚠️", "ADVISORY": "ℹ️"}
    return mapping.get(rule_level, "🔔")


def _escape_markdown(text: str) -> str:
    """Escapes special characters for Telegram Markdown (V1)."""
    if not isinstance(text, str):
        return str(text)
    # Characters that need escaping in MarkdownV1: _ * ` [
    for char in ["_", "*", "`", "["]:
        text = text.replace(char, f"\\{char}")
    return text


async def send_guardrail_alert(
    rule_id: str,
    regulation: str,
    section: str,
    vendor_name: str,
    amount_inr: float,
    violation_detail: str,
    action_taken: str,
    run_id: str,
    rule_level: str = "SOFT_FLAG",
    tester_name: str = "Unknown",
    tester_role: str = "USER",
) -> bool:
    """Send formatted Telegram message when a guardrail fires."""
    if not _bot_available:
        logger.warning("[Telegram] Bot not configured — skipping guardrail alert.")
        return False

    emoji = _level_emoji(rule_level)
    label = rule_level.replace("_", " ")
    
    e_tester = _escape_markdown(tester_name)
    e_role = _escape_markdown(tester_role)
    e_vendor = _escape_markdown(vendor_name)
    e_section = _escape_markdown(section)

    message = (
        f"{emoji} *{label} — FinClosePilot Alert*\n\n"
        f"*Tester:* {e_tester} ({e_role})\n"
        f"*Vendor:* {e_vendor}\n"
        f"*Amount:* Rs {_format_inr(amount_inr)}\n"
        f"*Rule:* {regulation}\n"
        f"*Section:* {e_section}\n"
        f"*Issue:* {violation_detail}\n\n"
        f"*Action taken:* {action_taken}\n"
        f"*Run ID:* `{run_id}`\n\n"
        f"/approve\\_{run_id} | /view\\_{run_id}"
    )

    return await _send_message(message)


async def send_anomaly_alert(
    category: str,
    severity: str,
    vendor_name: str,
    financial_exposure_inr: float,
    reasoning: str,
    run_id: str,
    tester_name: str = "Unknown",
    tester_role: str = "USER",
) -> bool:
    """Send Telegram message when CRITICAL or HIGH anomaly is detected."""
    if not _bot_available:
        logger.warning("[Telegram] Bot not configured — skipping anomaly alert.")
        return False

    if severity not in ("CRITICAL", "HIGH"):
        return False

    e_tester = _escape_markdown(tester_name)
    e_role = _escape_markdown(tester_role)
    e_vendor = _escape_markdown(vendor_name)
    e_cat = _escape_markdown(category)

    message = (
        f"🚨 *{severity} ANOMALY — FinClosePilot*\n\n"
        f"*Tester:* {e_tester} ({e_role})\n"
        f"*Type:* {e_cat}\n"
        f"*Vendor:* {e_vendor}\n"
        f"*Exposure:* Rs {_format_inr(financial_exposure_inr)}\n"
        f"*Finding:* {reasoning[:300]}\n\n"
        f"/review\\_{run_id}"
    )

    return await _send_message(message)


async def send_pipeline_complete(
    run_id: str,
    matched: int,
    breaks: int,
    anomalies: int,
    guardrail_fires: int,
    time_taken_seconds: float,
    total_blocked_inr: float,
    period: str = "Q3 FY26",
    tester_name: str = "Unknown",
    tester_role: str = "USER",
) -> bool:
    """Send summary message when full pipeline completes."""
    if not _bot_available:
        logger.warning("[Telegram] Bot not configured — skipping pipeline complete alert.")
        return False

    minutes = int(time_taken_seconds // 60)
    seconds = int(time_taken_seconds % 60)
    time_str = f"{minutes}m {seconds}s"

    e_tester = _escape_markdown(tester_name)
    e_role = _escape_markdown(tester_role)
    e_period = _escape_markdown(period)

    message = (
        f"✅ *Financial Close Complete — FinClosePilot*\n\n"
        f"*Tester:* {e_tester} ({e_role})\n"
        f"*Period:* {e_period}\n"
        f"*Time taken:* {time_str}\n"
        f"*Records:* {matched:,} matched | {breaks} breaks\n"
        f"*Anomalies:* {anomalies} found\n"
        f"*Guardrails:* {guardrail_fires} fired\n"
        f"*ITC Blocked:* Rs {_format_inr(total_blocked_inr)}\n\n"
        f"Full report ready at `/api/runs/{run_id}`"
    )

    return await _send_message(message)


async def send_test_message() -> bool:
    """Send a test connectivity message to the CFO chat."""
    if not _bot_available:
        logger.warning("[Telegram] Bot not configured — cannot send test message.")
        return False
    return await _send_message("✅ *FinClosePilot connected* — Telegram alerts are working!")


async def _send_message(text: str) -> bool:
    """Internal: sends a message to the CFO chat using python-telegram-bot."""
    try:
        from telegram import Bot
        from telegram.constants import ParseMode

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=TELEGRAM_CFO_CHAT_ID,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
            )
        logger.info("[Telegram] Message sent successfully.")
        return True
    except ImportError:
        logger.warning("[Telegram] python-telegram-bot not installed — skipping.")
        return False
    except Exception as e:
        logger.warning(f"[Telegram] Failed to send message: {e}")
        return False


async def setup_telegram_handlers(application) -> None:
    """Sets up /approve_*, /view_*, /review_* command handlers."""
    try:
        from telegram.ext import CommandHandler

        async def approve_handler(update, context):
            run_id = context.args[0] if context.args else "unknown"
            await update.message.reply_text(f"✅ Run {run_id} approved by CFO.")

        async def view_handler(update, context):
            run_id = context.args[0] if context.args else "unknown"
            await update.message.reply_text(f"📊 View run: http://localhost:3000?run={run_id}")

        async def review_handler(update, context):
            run_id = context.args[0] if context.args else "unknown"
            await update.message.reply_text(f"🔍 Reviewing anomaly in run: {run_id}")

        application.add_handler(CommandHandler("approve", approve_handler))
        application.add_handler(CommandHandler("view", view_handler))
        application.add_handler(CommandHandler("review", review_handler))
    except Exception as e:
        logger.warning(f"[Telegram] setup_telegram_handlers failed: {e}")


async def start_telegram_bot() -> None:
    """Starts the Telegram bot polling in the background."""
    global _application

    if not _bot_available:
        logger.warning("[Telegram] Bot token/chat ID not set — bot not started.")
        return

    try:
        from telegram.ext import Application

        _application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        await setup_telegram_handlers(_application)
        await _application.initialize()
        await _application.start()

        # Start polling for incoming commands (approve, view, review)
        if _application.updater:
            await _application.updater.start_polling(drop_pending_updates=True)
            logger.info("[Telegram] Bot started and polling for commands.")
        else:
            logger.warning("[Telegram] Bot started but updater not available — commands won't work.")
    except ImportError:
        logger.warning("[Telegram] python-telegram-bot not installed.")
    except Exception as e:
        logger.warning(f"[Telegram] Bot startup failed: {e}")


async def stop_telegram_bot() -> None:
    """Graceful shutdown of the Telegram bot."""
    global _application
    if _application:
        try:
            if _application.updater and _application.updater.running:
                await _application.updater.stop()
            if _application.running:
                await _application.stop()
            await _application.shutdown()
            logger.info("[Telegram] Bot stopped gracefully.")
        except Exception as e:
            logger.warning(f"[Telegram] Bot shutdown error: {e}")
        _application = None
