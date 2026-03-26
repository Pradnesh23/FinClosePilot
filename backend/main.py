"""
FastAPI main application entry point for FinClosePilot.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS, DEBUG
from backend.database.models import init_db
from backend.api.routes import router, init_letta_on_startup
from backend.agents.additions.regulatory_monitor import start_periodic_regulatory_monitor
from backend.notifications.telegram_bot import stop_telegram_bot

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("[Startup] Initializing FinClosePilot...")
    os.makedirs("./data/demo", exist_ok=True)

    # Initialize SQLite tables
    init_db()

    # Initialize Letta client
    await init_letta_on_startup()

    # Import after Letta is initialized to get agent_id
    from backend.api.routes import get_letta
    lc, ag = get_letta()

    # Start Telegram bot in background
    try:
        from backend.notifications.telegram_bot import start_telegram_bot
        asyncio.create_task(start_telegram_bot())
    except Exception as e:
        logger.warning(f"[Startup] Telegram bot skipped: {e}")

    # Start periodic regulatory monitor (runs every 6 hours, first after 30s)
    asyncio.create_task(start_periodic_regulatory_monitor(lc, ag))

    logger.info("[Startup] FinClosePilot ready ✅")
    yield

    # Shutdown cleanup
    logger.info("[Shutdown] FinClosePilot shutting down...")
    await stop_telegram_bot()


app = FastAPI(
    title="FinClosePilot",
    description="India's First AI-Native Financial Close Automation Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
origins = [o.strip() for o in CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routes
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "FinClosePilot", "version": "1.0.0"}
