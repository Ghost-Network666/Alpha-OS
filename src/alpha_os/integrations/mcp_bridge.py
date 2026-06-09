"""MCPBridge — connect to configured MCP servers and list tools."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from alpha_os.integrations.mcp_discovery import (
    config_paths_status,
    discover_mcp_servers,
    discovery_sources,
)
from alpha_os.integrations.mcp_humanize import (
    build_category_summary,
    enrich_tool,
    humanize_tool_result,
)

logger = logging.getLogger("alpha_os.mcp")

_SAMPLE_ARGS: dict[str, dict[str, Any]] = {
    "alpha_discover_high_liquidity": {"limit": 3},
    "alpha_discover_active_btc_15m": {},
    "alpha_discover_ending_soon": {"limit": 3},
}


def _pick_sample_tool(tools: list[dict[str, Any]]) -> tuple[str, dict[str, Any]] | None:
    names = [t.get("name", "") for t in tools]
    for prefer in _SAMPLE_ARGS:
        if prefer in names:
            return prefer, dict(_SAMPLE_ARGS[prefer])
    for t in tools:
        n = str(t.get("name", "")).lower()
        if "discover" in n:
            return str(t["name"]), {}
    return None


class MCPBridge:
    """Single stdio MCP server connection."""

    def __init__(
        self,
        name_or_def: str | dict[str, Any],
        command: str = "",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        source: str = "",
    ):
        if isinstance(name_or_def, dict):
            d = name_or_def
            self.name = str(d.get("name") or "")
            self.command = str(d.get("command") or "")
            self.args = list(d.get("args") or [])
            self.env = dict(d.get("env") or {})
            self.source = str(d.get("source") or "")
            self.transport = str(d.get("transport") or "stdio")
            self.probeable = bool(d.get("probeable", True))
            self.definition = d
        else:
            self.name = name_or_def
            self.command = command
            self.args = args or []
            self.env = env or {}
            self.source = source
            self.transport = "stdio"
            self.probeable = True
            self.definition = {}
        self._connected = False
        self._tools: list[dict[str, Any]] = []
        self._error: str | None = None
        self._widgets: list[dict[str, Any]] = []

    def _server_params(self):
        from mcp import StdioServerParameters

        return StdioServerParameters(
            command=self.command,
            args=self.args,
            env={**dict(__import__("os").environ), **{k: str(v) for k, v in self.env.items()}},
        )

    async def _with_session(self, fn: Callable) -> Any:
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        params = self._server_params()
        async with asyncio.timeout(12):
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await fn(session)

    async def connect(self, *, sample_data: bool = True) -> bool:
        if not self.probeable:
            self._connected = False
            self._tools = []
            self._error = None
            return False
        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client
        except ImportError:
            self._error = "mcp package not installed (pip install mcp)"
            return False

        self._widgets = []
        try:
            async def _probe(session: ClientSession) -> list[dict[str, Any]]:
                result = await session.list_tools()
                return [
                    {
                        "name": t.name,
                        "description": (t.description or "")[:240],
                    }
                    for t in (result.tools or [])
                ]

            tools = await self._with_session(_probe)
            self._tools = tools
            self._connected = True
            self._error = None
            if sample_data:
                await self._fetch_sample_widget()
            return True
        except Exception as e:
            logger.warning("MCP %s offline: %s", self.name, e)
            self._connected = False
            self._error = str(e)[:200]
            self._tools = []
            self._widgets = []
            return False

    async def _fetch_sample_widget(self) -> None:
        pick = _pick_sample_tool(self._tools)
        if not pick:
            return
        tool_name, args = pick
        desc = next((t.get("description", "") for t in self._tools if t.get("name") == tool_name), "")
        try:
            widget = await self.call_tool(tool_name, args)
            self._widgets = [
                humanize_tool_result(
                    server=self.name,
                    tool_name=tool_name,
                    description=desc,
                    raw=widget.get("result"),
                    ok=widget.get("ok", False),
                    error=widget.get("error"),
                )
            ]
        except Exception as exc:
            self._widgets = [
                humanize_tool_result(
                    server=self.name,
                    tool_name=tool_name,
                    description=desc,
                    raw=None,
                    ok=False,
                    error=str(exc)[:200],
                )
            ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.command:
            return {"ok": False, "error": "No MCP command configured"}

        async def _call(session) -> Any:
            return await session.call_tool(tool_name, arguments or {})

        try:
            result = await self._with_session(_call)
            payload: Any = result
            if hasattr(result, "model_dump"):
                payload = result.model_dump()
            elif hasattr(result, "content"):
                payload = {"content": getattr(result, "content")}
            return {"ok": True, "result": payload, "tool": tool_name, "server": self.name}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:300], "tool": tool_name, "server": self.name}

    def get_tools(self) -> list[dict[str, Any]]:
        return [enrich_tool(self._connected, t) for t in self._tools]

    def get_widgets(self) -> list[dict[str, Any]]:
        return list(self._widgets)

    def to_dict(self) -> dict[str, Any]:
        tools = self.get_tools()
        base: dict[str, Any] = {
            "name": self.name,
            "connected": self._connected,
            "transport": self.transport,
            "probeable": self.probeable,
            "tool_count": len(tools),
            "tools_online": sum(1 for t in tools if t.get("status") == "online"),
            "tools_offline": sum(1 for t in tools if t.get("status") == "offline"),
            "tools": tools,
            "categories": build_category_summary(tools),
            "widgets": self.get_widgets(),
            "error": self._error,
            "source": self.source,
        }
        if self.probeable:
            base["command"] = self.command
        else:
            base["url"] = self.definition.get("url")
            base["status"] = "configured"
        return base


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
            "widgets": [],
            "categories": [],
            "servers_online": 0,
            "servers_offline": 0,
            "tools_online": 0,
            "tools_offline": 0,
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

    def _empty_message(self, runtime: str) -> str:
        paths = config_paths_status()
        hermes = next((p for p in paths if p["runtime"] == "hermes"), None)
        openclaw = next((p for p in paths if p["runtime"] == "openclaw"), None)
        if runtime == "hermes":
            path = hermes["path"] if hermes else "~/.hermes/config.yaml"
            return f"No MCP servers in {path} — add mcp_servers entries (stdio command + args)"
        if runtime == "openclaw":
            path = openclaw["path"] if openclaw else "~/.openclaw/openclaw.json"
            return f"No MCP servers in {path} — add mcp.servers entries (stdio or remote)"
        return (
            "No MCP servers found — configure stdio MCP in "
            "~/.hermes/config.yaml (mcp_servers) or "
            "~/.openclaw/openclaw.json (mcp.servers)"
        )

    async def refresh(
        self,
        runtime: str | None = None,
        *,
        sample_data: bool = True,
    ) -> dict[str, Any]:
        import time

        active_runtime = (runtime or "auto").lower()
        defs = discover_mcp_servers(active_runtime)
        self._servers = [MCPBridge(d) for d in defs if d.get("name")]
        stdio = [s for s in self._servers if s.probeable and s.command]
        remote = [s for s in self._servers if not s.probeable]
        if not self._servers:
            empty_msg = self._empty_message(active_runtime)
            self._data = {
                "connected": False,
                "server_count": 0,
                "tool_count": 0,
                "servers": [],
                "widgets": [],
                "categories": [],
                "servers_online": 0,
                "servers_offline": 0,
                "tools_online": 0,
                "tools_offline": 0,
                "runtime": active_runtime,
                "error": empty_msg,
                "summary": empty_msg,
                "config_paths": config_paths_status(),
                "sources": discovery_sources(),
            }
            self._last_scan = time.time()
            return dict(self._data)

        results = await asyncio.gather(
            *[s.connect(sample_data=sample_data) for s in stdio],
            return_exceptions=True,
        )
        servers_out = [s.to_dict() for s in remote]
        widgets: list[dict[str, Any]] = []
        all_tools: list[dict[str, Any]] = []
        total_tools = 0
        tools_online = 0
        tools_offline = 0
        servers_online = 0
        any_connected = bool(remote)

        for bridge, res in zip(stdio, results):
            if isinstance(res, Exception):
                bridge._error = str(res)[:200]
            if bridge._connected:
                any_connected = True
                servers_online += 1
            tools = bridge.get_tools()
            all_tools.extend(tools)
            total_tools += len(tools)
            tools_online += sum(1 for t in tools if t.get("status") == "online")
            tools_offline += sum(1 for t in tools if t.get("status") == "offline")
            widgets.extend(bridge.get_widgets())
            servers_out.append(bridge.to_dict())

        servers_offline = len(stdio) - servers_online

        self._data = {
            "connected": any_connected,
            "server_count": len(self._servers),
            "stdio_count": len(stdio),
            "remote_count": len(remote),
            "runtime": active_runtime,
            "tool_count": total_tools,
            "servers_online": servers_online,
            "servers_offline": servers_offline,
            "tools_online": tools_online,
            "tools_offline": tools_offline,
            "servers": servers_out,
            "widgets": widgets,
            "categories": build_category_summary(all_tools),
            "sources": discovery_sources(),
            "error": None if any_connected else "All stdio MCP servers offline",
        }
        self._last_scan = time.time()
        return dict(self._data)

    async def call_tool(self, server: str, tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        bridge = next((s for s in self._servers if s.name == server), None)
        if not bridge:
            bridge = next((s for s in self._load_definitions() if s.name == server), None)
        if not bridge:
            return {"ok": False, "error": f"MCP server '{server}' not found"}
        result = await bridge.call_tool(tool, arguments)
        if result.get("ok"):
            desc = ""
            for t in bridge._tools:
                if t.get("name") == tool:
                    desc = str(t.get("description", ""))
                    break
            widget = humanize_tool_result(
                server=server,
                tool_name=tool,
                description=desc,
                raw=result.get("result"),
                ok=True,
            )
            result["widget"] = widget
        return result

    def get_panel_data(self) -> dict[str, Any]:
        return dict(self._data)