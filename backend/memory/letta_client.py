"""
Letta memory client for FinClosePilot.
Connects to self-hosted Letta server with full SQLite fallback.
"""

import json
import logging
import warnings
from datetime import datetime
from typing import Any

from backend.config import LETTA_SERVER_URL, LETTA_AGENT_ID

logger = logging.getLogger(__name__)

# ─── Optional Letta import (graceful if not installed) ──────────────────────
try:
    from letta import create_client
    LETTA_AVAILABLE = True
except ImportError:
    try:
        from letta_client import create_client
        LETTA_AVAILABLE = True
    except ImportError:
        LETTA_AVAILABLE = False
        warnings.warn("[Letta] 'letta' package not installed — using SQLite fallback.")


# ─── SQLite Fallback Helpers ────────────────────────────────────────────────
def _sqlite_store(agent_id: str, memory_type: str, label: str, content: Any) -> None:
    from backend.database.models import get_db_connection
    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT INTO letta_fallback (agent_id, memory_type, label, content, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (agent_id, memory_type, label, json.dumps(content), datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def _sqlite_search(agent_id: str, query: str, limit: int = 10) -> list:
    from backend.database.models import get_db_connection
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """SELECT content FROM letta_fallback
               WHERE agent_id = ? AND content LIKE ?
               ORDER BY id DESC LIMIT ?""",
            (agent_id, f"%{query}%", limit),
        ).fetchall()
        results = []
        for row in rows:
            try:
                results.append(json.loads(row[0]))
            except Exception:
                results.append({"raw": row[0]})
        return results
    finally:
        conn.close()


def _sqlite_get_label(agent_id: str, label: str) -> Any:
    from backend.database.models import get_db_connection
    conn = get_db_connection()
    try:
        row = conn.execute(
            """SELECT content FROM letta_fallback
               WHERE agent_id = ? AND label = ?
               ORDER BY id DESC LIMIT 1""",
            (agent_id, label),
        ).fetchone()
        if row:
            return json.loads(row[0])
        return None
    finally:
        conn.close()


# ─── Letta Client Wrapper ────────────────────────────────────────────────────
class LettaClientWrapper:
    """
    Thin wrapper around the Letta Python SDK.
    Falls back to SQLite automatically on any failure.
    """

    def __init__(self):
        self.client = None
        self._use_fallback = True

        if LETTA_AVAILABLE:
            try:
                self.client = create_client(base_url=LETTA_SERVER_URL)
                self._use_fallback = False
                logger.info(f"[Letta] Connected to {LETTA_SERVER_URL}")
            except Exception as e:
                logger.warning(f"[Letta] Could not connect: {e} — using SQLite fallback")
        else:
            logger.warning("[Letta] Using SQLite fallback (letta not installed)")


def init_letta_client() -> LettaClientWrapper:
    """Returns an initialised Letta wrapper (or fallback)."""
    return LettaClientWrapper()


async def create_or_get_agent(client: LettaClientWrapper, name: str = "FinClosePilot") -> str:
    """
    Creates or retrieves the Letta agent.
    Returns agent_id string.
    """
    if LETTA_AGENT_ID:
        return LETTA_AGENT_ID

    if client._use_fallback:
        agent_id = f"fallback_{name}"
        logger.warning(f"[Letta] Using fallback agent_id: {agent_id}")
        return agent_id

    try:
        # Try to list existing agents and find by name
        agents = client.client.list_agents()
        for agent in agents:
            if agent.name == name:
                logger.info(f"[Letta] Reusing existing agent: {agent.id}")
                return agent.id

        # Create new agent with memory blocks
        from letta import AgentState
        from letta.schemas.memory import ChatMemory

        memory = ChatMemory(
            human="Finance team running the quarterly close pipeline.",
            persona=(
                "You are FinClosePilot, an AI-native financial close agent for India. "
                "You have deep knowledge of GST, SEBI LODR, IndAS, and Income Tax regulations."
            ),
        )

        agent_state: AgentState = client.client.create_agent(
            name=name,
            memory=memory,
        )
        logger.info(f"[Letta] Created new agent: {agent_state.id}")
        return agent_state.id

    except Exception as e:
        logger.warning(f"[Letta] create_or_get_agent failed: {e} — using fallback")
        return f"fallback_{name}"


async def store_to_archival(client: LettaClientWrapper, agent_id: str, data_dict: dict, label: str = "archival") -> None:
    """Insert JSON data to archival memory with an optional label."""
    if client._use_fallback or agent_id.startswith("fallback_"):
        _sqlite_store(agent_id, "archival", label, data_dict)
        return
    try:
        text = f"[{label}] {json.dumps(data_dict)}" if label != "archival" else json.dumps(data_dict)
        client.client.insert_archival_memory(agent_id=agent_id, memory=text)
    except Exception as e:
        logger.warning(f"[Letta] store_to_archival failed: {e} — using fallback")
        _sqlite_store(agent_id, "archival", label, data_dict)


async def get_archival_by_label(client: LettaClientWrapper, agent_id: str, label: str) -> Any:
    """Retrieve the latest archival entry with a specific label."""
    if client._use_fallback or agent_id.startswith("fallback_"):
        return _sqlite_get_label(agent_id, label)
    
    try:
        # Note: Letta SDK might use get_archival_memory or similar
        # For now, we rely on the fallback or common search pattern
        results = client.client.get_archival_memory(agent_id=agent_id, limit=50)
        for r in results:
            if r.text.startswith(f"[{label}] "):
                json_str = r.text.replace(f"[{label}] ", "", 1)
                return json.loads(json_str)
        return None
    except Exception:
        # Fallback to sqlite if SDK call fails or method name is different
        return _sqlite_get_label(agent_id, label)


async def search_recall(client: LettaClientWrapper, agent_id: str, query: str, limit: int = 10) -> list:
    """Semantic archival search."""
    if client._use_fallback or agent_id.startswith("fallback_"):
        return _sqlite_search(agent_id, query, limit)
    try:
        results = client.client.get_archival_memory(
            agent_id=agent_id, query=query, limit=limit
        )
        return [json.loads(r.text) if r.text.startswith("{") else {"text": r.text} for r in results]
    except Exception as e:
        logger.warning(f"[Letta] search_recall failed: {e}")
        return _sqlite_search(agent_id, query, limit)


async def update_core(client: LettaClientWrapper, agent_id: str, label: str, value: Any) -> None:
    """Update a named core memory block."""
    if client._use_fallback or agent_id.startswith("fallback_"):
        _sqlite_store(agent_id, "core", label, value)
        return
    try:
        client.client.update_in_context_memory(
            agent_id=agent_id, section=label, value=json.dumps(value)
        )
    except Exception as e:
        logger.warning(f"[Letta] update_core failed: {e}")
        _sqlite_store(agent_id, "core", label, value)


async def get_vendor_history(client: LettaClientWrapper, agent_id: str, vendor_name: str) -> list:
    """Query vendor patterns from archival memory."""
    return await search_recall(client, agent_id, f"vendor {vendor_name}", limit=5)


async def get_period_patterns(client: LettaClientWrapper, agent_id: str, period_type: str) -> list:
    """Fetch historical patterns for a period type (e.g., 'Q3', 'month_end')."""
    return await search_recall(client, agent_id, f"close_duration {period_type}", limit=10)


async def store_guardrail_fire(client: LettaClientWrapper, agent_id: str, guardrail_data: dict) -> None:
    """Log a guardrail firing event to archival memory."""
    payload = {"type": "guardrail_fire", **guardrail_data, "ts": datetime.utcnow().isoformat()}
    await store_to_archival(client, agent_id, payload)


async def store_rlhf_signal(client: LettaClientWrapper, agent_id: str, signal_data: dict) -> None:
    """Store human correction signal to archival memory."""
    payload = {"type": "rlhf_signal", **signal_data, "ts": datetime.utcnow().isoformat()}
    await store_to_archival(client, agent_id, payload)


async def query_audit_trail(client: LettaClientWrapper, agent_id: str, question: str) -> list:
    """NL query on archival memory for audit trail questions."""
    return await search_recall(client, agent_id, question, limit=20)


async def store_regulatory_update(client: LettaClientWrapper, agent_id: str, update_data: dict) -> None:
    """Store a new regulatory update to archival memory."""
    payload = {
        "type": "regulatory_update",
        **update_data,
        "stored_at": datetime.utcnow().isoformat(),
    }
    await store_to_archival(client, agent_id, payload)
    # Also update core memory with regulatory version
    await update_core(client, agent_id, "regulatory_rules_version", {
        "version": datetime.utcnow().strftime("v%Y.%m.%d"),
        "last_updated": datetime.utcnow().isoformat(),
        "framework": update_data.get("framework"),
    })


async def get_regulatory_rules(client: LettaClientWrapper, agent_id: str, framework: str) -> list:
    """Fetch current rules for a regulatory framework."""
    return await search_recall(client, agent_id, f"regulatory_update {framework}", limit=10)


async def seed_past_period_data(client: LettaClientWrapper, agent_id: str, data: dict) -> None:
    """Seed Letta archival memory with past period data from JSON."""
    for vendor in data.get("vendor_patterns", []):
        await store_to_archival(client, agent_id, {"type": "vendor_pattern", **vendor})

    for duration in data.get("past_close_durations", []):
        await store_to_archival(client, agent_id, {"type": "close_duration", **duration})

    for resolution in data.get("past_anomaly_resolutions", []):
        await store_to_archival(client, agent_id, {"type": "anomaly_resolution", **resolution})

    for fire in data.get("past_guardrail_fires", []):
        await store_to_archival(client, agent_id, {"type": "guardrail_history", **fire})

    for budget in data.get("budget_actuals_history", []):
        await store_to_archival(client, agent_id, {"type": "budget_history", **budget})

    await update_core(client, agent_id, "org_policy", {
        "regulatory_rules_version": data.get("regulatory_rules_version", "v1.0"),
        "last_regulatory_check": data.get("last_regulatory_check"),
    })
    logger.info("[Letta] Seeded past period data to archival memory.")
