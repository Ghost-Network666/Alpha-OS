"""MCPBridge — connect to configured MCP servers and list tools."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from alpha_os.integrations.mcp_discovery import discover_mcp_servers, discovery_sources

logger = logging.getLogger("alpha_os.mcp")


class MCPBridge:
    """Single stdio MCP server connection."""

    def __init__(
        self,
        name: str,
        command: str,
        args: list[str],
        env: dict[str, str],
        source: str = "",
    ):
        self.name = name
        self.command = command
        self.args = args
        self.env = env
        self.source = source
        self._connected = False
        self._tools: list[dict[str, Any]] = []
        self._error: str | None = None

    async def connect(self) -> bool:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            self._error = "mcp package not installed (pip install alpha-os[voice])"
            return False

        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env={**dict(__import__("os").environ), **{k: str(v) for k, v in self.env.items()}},
        )
        try:
            async with asyncio.timeout(8):
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        self._tools = [
                            {
                                "name": t.name,
                                "description": (t.description or "")[:120],
                            }
                            for t in (result.tools or [])
                        ]
                        self._connected = True
                        self._error = None
                        return True
        except Exception as e:
            logger.warning("MCP %s offline: %s", self.name, e)
            self._connected = False
            self._error = str(e)[:200]
            self._tools = []
            return False

    def get_tools(self) -> list[dict[str, Any]]:
        return list(self._tools)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "connected": self._connected,
            "transport": "stdio",
            "tool_count": len(self._tools),
            "tools": self._tools[:12],
            "error": self._error,
            "command": self.command,
            "source": self.source,
        }


class MCPRegistry:
    """Discover and probe all configured MCP servers."""

    def __init__(self):
        self._servers: list[MCPBridge] = []
        self._last_scan: float | None = None
        self._data: dict[str, Any] = {
            "connected": False,
            "server_count": 0,
            "tool_count": 0,
            "servers": [],
            "error": None,
        }

    def _load_definitions(self) -> list[MCPBridge]:
        defs = discover_mcp_servers()
        return [
            MCPBridge(
                name=d["name"],
                command=d["command"] or "",
                args=d.get("args") or [],
                env=d.get("env") or {},
                source=str(d.get("source") or ""),
            )
            for d in defs
            if d.get("transport") == "stdio" and d.get("command")
        ]

    async def refresh(self) -> dict[str, Any]:
        import time

        self._servers = self._load_definitions()
        if not self._servers:
            self._data = {
                "connected": False,
                "server_count": 0,
                "tool_count": 0,
                "servers": [],
                "error": (
                    "No stdio MCP servers found — configure mcp_servers in "
                    "~/.hermes/config.yaml or mcp.servers in ~/.openclaw/openclaw.json"
                ),
                "sources": discovery_sources(),
            }
            self._last_scan = time.time()
            return dict(self._data)

        results = await asyncio.gather(
            *[s.connect() for s in self._servers],
            return_exceptions=True,
        )
        servers_out = []
        total_tools = 0
        any_connected = False
        for bridge, res in zip(self._servers, results):
            if isinstance(res, Exception):
                bridge._error = str(res)[:200]
            if bridge._connected:
                any_connected = True
            total_tools += len(bridge.get_tools())
            servers_out.append(bridge.to_dict())

        self._data = {
            "connected": any_connected,
            "server_count": len(self._servers),
            "tool_count": total_tools,
            "servers": servers_out,
            "sources": discovery_sources(),
            "error": None if any_connected else "All stdio MCP servers offline",
        }
        self._last_scan = time.time()
        return dict(self._data)

    def get_panel_data(self) -> dict[str, Any]:
        return dict(self._data)