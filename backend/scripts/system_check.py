import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("SystemCheck")

# Add project root directory to module search path so backend imports work
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

def check_env_vars():
    """Verify all required environment variables are present and valid."""
    logger.info("--- Checking Environment Variables ---")
    
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        logger.error(f"❌ .env file missing at {env_path}")
        return False
        
    load_dotenv(env_path)
    
    required_keys = ["GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CFO_CHAT_ID", "LETTA_AGENT_ID"]
    passed = True
    
    for key in required_keys:
        val = os.getenv(key)
        if not val:
            logger.error(f"❌ {key} is missing or empty")
            passed = False
        else:
            logger.info(f"✅ {key} is configured")
            
    # Optional DB check
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./finclose.db")
    logger.info(f"ℹ️ DATABASE_URL uses: {db_url}")
    
    return passed


async def check_database():
    """Verify database connection and schema."""
    logger.info("--- Checking Database Connection ---")
    try:
        from backend.database.models import get_db_connection
        
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def check_letta():
    """Verify Letta service is reachable."""
    logger.info("--- Checking Letta Connection ---")
    client = None
    try:
        from backend.memory.letta_client import get_letta_client
        client = get_letta_client()
        # Verify agent exists
        agent_id = os.getenv("LETTA_AGENT_ID")
        if not agent_id:
            return False
            
        agent = client.get_agent(agent_id=agent_id)
        if agent:
            logger.info(f"✅ Letta connection successful. Found agent: {agent.name}")
            return True
        else:
            logger.error("❌ Letta connected but agent not found")
            return False
    except Exception as e:
        logger.error(f"❌ Letta connection failed: {e}")
        return False


async def check_gemini():
    """Verify Gemini API key works."""
    logger.info("--- Checking Gemini API ---")
    try:
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Respond with a checkmark if you see this."
        )
        if response.text:
            logger.info("✅ Gemini API call successful")
            return True
        else:
            logger.error("❌ Gemini API returned empty response")
            return False
    except Exception as e:
        logger.error(f"❌ Gemini API call failed: {e}")
        return False


async def check_telegram():
    """Verify Telegram Bot token is valid."""
    logger.info("--- Checking Telegram Bot ---")
    try:
        from telegram import Bot
        # Use python-telegram-bot v20+ async test
        bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
        async with bot:
            me = await bot.get_me()
        logger.info(f"✅ Telegram bot connected as: @{me.username}")
        return True
    except Exception as e:
        logger.error(f"❌ Telegram bot connect failed: {e}")
        return False


async def run_all_checks():
    """Run all system checks sequentially."""
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
            
    print("\n" + "="*50)
    print("🚀 FINCLOSEPILOT SYSTEM DIAGNOSTICS")
    print("="*50 + "\n")
    
    env_ok = check_env_vars()
    if not env_ok:
        print("\n⚠️ Fix environment variables before running other checks.\n")
        return

    db_ok = await check_database()
    gemini_ok = await check_gemini()
    letta_ok = await check_letta()
    tg_ok = await check_telegram()
    
    print("\n" + "="*50)
    print("📊 DIAGNOSTICS SUMMARY")
    print("="*50)
    print(f"Environment: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"Database:    {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"Gemini API:  {'✅ PASS' if gemini_ok else '❌ FAIL'}")
    print(f"Letta Core:  {'✅ PASS' if letta_ok else '❌ FAIL'}")
    print(f"Telegram:    {'✅ PASS' if tg_ok else '❌ FAIL'}")
    print("="*50)
    
    if all([env_ok, db_ok, gemini_ok, letta_ok, tg_ok]):
        print("🎉 ALL SYSTEMS GO! The backend is ready to run.")
        print("▶️ Run: uvicorn backend.main:app --reload")
        sys.exit(0)
    else:
        print("⚠️ Some checks failed. Please review the logs above.")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    
    # Supress noisy httpx logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    asyncio.run(run_all_checks())
