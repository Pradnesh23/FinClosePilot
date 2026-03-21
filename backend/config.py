from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
LETTA_SERVER_URL = os.getenv("LETTA_SERVER_URL", "http://localhost:8283")
LETTA_AGENT_ID = os.getenv("LETTA_AGENT_ID", "")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "./data/finclosepilot.db")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CFO_CHAT_ID = os.getenv("TELEGRAM_CFO_CHAT_ID", "")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
