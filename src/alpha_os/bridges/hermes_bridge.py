"""Hermes Agent API server bridge (port 8642 REST + SSE)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Optional

import httpx

from alpha_os.bridges.detector import PALETTE, color_for_index

logger = logging.getLogger("alpha_os.hermes")


class HermesBridge:
    def __init__(
        self,
        gateway_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.gateway_url = (
            gateway_url
            or os.getenv("HERMES_GATEWAY_URL", "http://127.0.0.1:8642")
        ).rstrip("/")
        self.api_key = api_key or os.getenv("HERMES_API_KEY", "") or os.getenv(
            "API_SERVER_KEY", ""
        )
        self._connected = False
        self._agents: list[dict[str, Any]] = []
        self._toolsets: list[dict[str, Any]] = []
        self._skills: list[dict[str, Any]] = []
        self._sessions: list[dict[str, Any]] = []
        self._capabilities: dict[str, Any] = {}
        self._last_event: dict[str, Any] = {}

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def connect(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                for path in ("/health", "/v1/health", "/v1/models"):
                    try:
                        r = await client.get(
                            f"{self.gateway_url}{path}",
                            headers=self._headers(),
                        )
                        if r.status_code == 200:
                            self._connected = True
                            await self._fetch_all(client)
                            return True
                    except Exception:
                        continue
        except Exception as e:
            logger.warning("Hermes gateway offline: %s", e)
        self._connected = False
        return False

    async def _fetch_all(self, client: httpx.AsyncClient) -> None:
        await self._fetch_capabilities(client)
        await self._fetch_toolsets(client)
        await self._fetch_skills(client)
        await self._fetch_sessions(client)
        self._build_agent_cards()

    async def _fetch_capabilities(self, client: httpx.AsyncClient) -> None:
        try:
            r = await client.get(
                f"{self.gateway_url}/v1/capabilities",
                headers=self._headers(),
            )
            if r.status_code == 200:
                self._capabilities = r.json()
        except Exception:
            self._capabilities = {}

    async def _fetch_toolsets(self, client: httpx.AsyncClient) -> None:
        try:
            r = await client.get(
                f"{self.gateway_url}/v1/toolsets",
                headers=self._headers(),
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    self._toolsets = data
                elif isinstance(data, dict):
                    self._toolsets = data.get("toolsets", data.get("data", []))
        except Exception:
            self._toolsets = []

    async def _fetch_skills(self, client: httpx.AsyncClient) -> None:
        try:
            r = await client.get(
                f"{self.gateway_url}/v1/skills",
                headers=self._headers(),
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    self._skills = data
                elif isinstance(data, dict):
                    self._skills = data.get("skills", data.get("data", []))
        except Exception:
            self._skills = []

    async def _fetch_sessions(self, client: httpx.AsyncClient) -> None:
        try:
            r = await client.get(
                f"{self.gateway_url}/api/sessions",
                headers=self._headers(),
                params={"limit": 20},
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    self._sessions = data
                elif isinstance(data, dict):
                    self._sessions = data.get("sessions", data.get("data", []))
        except Exception:
            self._sessions = []

    async def _fetch_agents(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                for path in ("/v1/agents", "/v1/profiles"):
                    try:
                        r = await client.get(
                            f"{self.gateway_url}{path}",
                            headers=self._headers(),
                        )
                        if r.status_code != 200:
                            continue
                        data = r.json()
                        items = data if isinstance(data, list) else data.get(
                            "agents", data.get("profiles", data.get("data", []))
                        )
                        if not isinstance(items, list):
                            continue
                        cards = []
                        for i, item in enumerate(items):
                            if not isinstance(item, dict):
                                continue
                            status_raw = str(
                                item.get("status", item.get("state", "Ready"))
                            ).lower()
                            cards.append({
                                "name": item.get("name", item.get("id", f"agent-{i}")),
                                "title": item.get("title", item.get("description", "")),
                                "status": "ACTIVE" if status_raw == "active" else "Ready",
                                "color": color_for_index(i),
                            })
                        if cards:
                            self._agents = cards
                            return
                    except Exception:
                        continue
        except Exception:
            pass

    def _build_agent_cards(self) -> None:
        cards: list[dict[str, Any]] = []
        idx = 0
        for ts in self._toolsets:
            if not isinstance(ts, dict):
                continue
            name = ts.get("name", ts.get("label", f"toolset-{idx}"))
            tools = ts.get("tools", [])
            tool_count = len(tools) if isinstance(tools, list) else 0
            enabled = ts.get("enabled", True)
            cards.append({
                "name": name,
                "title": f"Toolset • {tool_count} tools",
                "status": "ACTIVE" if enabled else "OFFLINE",
                "color": color_for_index(idx),
                "tool_count": tool_count,
            })
            idx += 1
        for sk in self._skills[:10]:
            if not isinstance(sk, dict):
                continue
            name = sk.get("name", f"skill-{idx}")
            cards.append({
                "name": name,
                "title": sk.get("description", "Skill")[:60],
                "status": "Ready",
                "color": color_for_index(idx),
            })
            idx += 1
        for sess in self._sessions[:5]:
            if not isinstance(sess, dict):
                continue
            sid = sess.get("id", sess.get("session_id", f"session-{idx}"))
            model = sess.get("model", "")
            cards.append({
                "name": str(sid)[:24],
                "title": model or sess.get("title", "Session"),
                "status": "ACTIVE" if sess.get("active") else "Ready",
                "color": color_for_index(idx),
            })
            idx += 1
        self._agents = cards

    async def stream_events(self, callback: Callable[[dict], None]) -> None:
        url = f"{self.gateway_url}/v1/runs/stream"
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET",
                    url,
                    headers={**self._headers(), "Accept": "text/event-stream"},
                ) as resp:
                    if resp.status_code != 200:
                        return
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            event = json.loads(line[6:])
                            self._last_event = event
                            callback(event)
                        except Exception:
                            pass
        except Exception as e:
            logger.warning("Hermes SSE disconnected: %s", e)
            self._connected = False

    def get_agent_list(self) -> list[dict[str, Any]]:
        return list(self._agents)

    def get_toolsets(self) -> list[dict[str, Any]]:
        return list(self._toolsets)

    def get_skills(self) -> list[dict[str, Any]]:
        return list(self._skills)

    def get_sessions(self) -> list[dict[str, Any]]:
        return list(self._sessions)

    def get_status(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "gateway_url": self.gateway_url,
            "agent_count": len(self._agents),
            "toolset_count": len(self._toolsets),
            "skill_count": len(self._skills),
            "session_count": len(self._sessions),
            "capabilities": self._capabilities,
            "last_event": self._last_event,
        }

    async def disconnect(self) -> None:
        self._connected = False