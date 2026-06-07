"""OpenClaw Gateway WebSocket bridge."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Callable, Optional

import websockets
from websockets.asyncio.client import connect as ws_connect

from alpha_os.bridges.detector import color_for_index

logger = logging.getLogger("alpha_os.openclaw")


class OpenClawBridge:
    def __init__(
        self,
        ws_url: Optional[str] = None,
        token: Optional[str] = None,
    ):
        raw = ws_url or os.getenv(
            "OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789"
        )
        self.ws_url = raw.replace("http://", "ws://").replace("https://", "wss://").rstrip("/")
        self.token = token or os.getenv("OPENCLAW_GATEWAY_TOKEN", "")
        self._connected = False
        self._ws: Any = None
        self._agents: list[dict[str, Any]] = []
        self._sessions: list[dict[str, Any]] = []
        self._channels: list[dict[str, Any]] = []
        self._last_event: dict[str, Any] = {}
        self._pending: dict[str, asyncio.Future] = {}
        self._event_callbacks: list[Callable[[dict], None]] = []
        self._recv_task: Optional[asyncio.Task] = None

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "alpha-os/0.1.0"}

    async def connect(self) -> bool:
        try:
            self._ws = await ws_connect(
                self.ws_url,
                additional_headers=self._headers(),
                open_timeout=5,
            )
            await self._handshake()
            self._recv_task = asyncio.create_task(self._recv_loop())
            await self._refresh_state()
            self._connected = True
            return True
        except Exception as e:
            logger.warning("OpenClaw gateway offline: %s", e)
            self._connected = False
            await self._cleanup()
            return False

    async def _handshake(self) -> None:
        assert self._ws is not None
        try:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=5)
            msg = json.loads(raw)
            if msg.get("type") == "event" and msg.get("event") == "connect.challenge":
                pass
        except asyncio.TimeoutError:
            pass

        req_id = str(uuid.uuid4())
        connect_req = {
            "type": "req",
            "id": req_id,
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 4,
                "client": {
                    "id": "alpha-os",
                    "version": "0.1.0",
                    "platform": "web",
                    "mode": "operator",
                },
                "role": "operator",
                "scopes": ["operator.read", "operator.write"],
                "caps": [],
                "commands": [],
                "permissions": {},
                "auth": {"token": self.token} if self.token else {},
                "locale": "en-US",
                "userAgent": "alpha-os/0.1.0",
            },
        }
        await self._ws.send(json.dumps(connect_req))
        raw = await asyncio.wait_for(self._ws.recv(), timeout=10)
        res = json.loads(raw)
        if res.get("type") == "res" and res.get("ok"):
            return
        raise ConnectionError(res.get("error", "handshake failed"))

    async def _rpc(self, method: str, params: Optional[dict] = None) -> Any:
        if not self._ws:
            return None
        req_id = str(uuid.uuid4())
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        await self._ws.send(json.dumps({
            "type": "req",
            "id": req_id,
            "method": method,
            "params": params or {},
        }))
        try:
            return await asyncio.wait_for(fut, timeout=10)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            return None

    async def _recv_loop(self) -> None:
        try:
            while self._ws:
                raw = await self._ws.recv()
                msg = json.loads(raw)
                if msg.get("type") == "res":
                    rid = msg.get("id")
                    fut = self._pending.pop(rid, None)
                    if fut and not fut.done():
                        if msg.get("ok"):
                            fut.set_result(msg.get("payload"))
                        else:
                            fut.set_result(None)
                elif msg.get("type") == "event":
                    self._last_event = msg
                    for cb in self._event_callbacks:
                        try:
                            cb(msg)
                        except Exception:
                            pass
        except Exception as e:
            logger.warning("OpenClaw WS disconnected: %s", e)
            self._connected = False

    async def _refresh_state(self) -> None:
        agents = await self._rpc("agents.list")
        if isinstance(agents, dict):
            items = agents.get("agents", agents.get("items", []))
        elif isinstance(agents, list):
            items = agents
        else:
            items = []
        cards = []
        for i, a in enumerate(items):
            if not isinstance(a, dict):
                continue
            cards.append({
                "name": a.get("id", a.get("name", f"agent-{i}")),
                "title": a.get("name", a.get("label", "")),
                "status": str(a.get("status", "Ready")).upper()
                if a.get("status") else "Ready",
                "color": color_for_index(i),
            })
        self._agents = cards

        sessions = await self._rpc("sessions.list")
        if isinstance(sessions, dict):
            self._sessions = sessions.get("sessions", sessions.get("items", []))
        elif isinstance(sessions, list):
            self._sessions = sessions
        else:
            self._sessions = []

        channels = await self._rpc("channels.status")
        if isinstance(channels, dict):
            self._channels = channels.get("channels", [channels])
        elif isinstance(channels, list):
            self._channels = channels
        else:
            self._channels = []

    def on_event(self, callback: Callable[[dict], None]) -> None:
        self._event_callbacks.append(callback)

    def get_agent_list(self) -> list[dict[str, Any]]:
        return list(self._agents)

    def get_status(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "gateway_url": self.ws_url,
            "agent_count": len(self._agents),
            "session_count": len(self._sessions),
            "channel_count": len(self._channels),
            "last_event": self._last_event,
        }

    def get_integrations(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "sessions": self._sessions,
            "channels": self._channels,
            "agents": self._agents,
            "last_updated": None,
            "error": None if self._connected else "OpenClaw gateway not connected",
        }

    async def send_command(self, text: str) -> dict[str, Any]:
        if not self._connected or not self._ws:
            return {"ok": False, "error": "OpenClaw gateway offline"}
        attempts = [
            ("chat.send", {"text": text}),
            ("chat.send", {"message": text}),
            ("sessions.send", {"text": text, "message": text}),
        ]
        last_error = "chat.send unavailable"
        for method, params in attempts:
            try:
                result = await self._rpc(method, params)
                if result is None:
                    continue
                reply = ""
                if isinstance(result, dict):
                    reply = (
                        result.get("text")
                        or result.get("message")
                        or result.get("output")
                        or result.get("reply")
                        or ""
                    )
                elif isinstance(result, str):
                    reply = result
                if reply or result is not None:
                    return {
                        "ok": True,
                        "reply": reply or "Sent to OpenClaw.",
                    }
            except Exception as e:
                last_error = str(e)[:200]
        return {"ok": False, "error": last_error}

    async def disconnect(self) -> None:
        self._connected = False
        await self._cleanup()

    async def _cleanup(self) -> None:
        if self._recv_task:
            self._recv_task.cancel()
            self._recv_task = None
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None