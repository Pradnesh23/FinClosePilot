"""
WebSocket connection manager for real-time agent activity feed.
"""

import json
import logging
from datetime import datetime
from typing import Callable
from fastapi import WebSocket # type: ignore

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections per run_id."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(run_id, []).append(websocket)
        logger.info(f"[WS] Client connected for run {run_id}")

    def disconnect(self, run_id: str, websocket: WebSocket) -> None:
        if run_id in self._connections:
            try:
                self._connections[run_id].remove(websocket)
            except ValueError:
                pass
        logger.info(f"[WS] Client disconnected from run {run_id}")

    async def broadcast(self, run_id: str, message: dict) -> None:
        """Broadcast a JSON message to all clients watching this run."""
        if run_id not in self._connections:
            return
        dead = []
        for ws in self._connections[run_id]:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[run_id].remove(ws)

    def make_callback(self, run_id: str) -> Callable:
        """Returns an async callback function for pipeline steps to broadcast."""
        async def callback(event: str, agent: str, data: dict = None, status: str = "RUNNING"): # type: ignore
            await self.broadcast(run_id, {
                "event": event,
                "agent": agent,
                "status": status,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat(),
                "run_id": run_id,
            })
        return callback


# Singleton instance
manager = WebSocketManager()
