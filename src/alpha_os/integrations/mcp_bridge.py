"""MCP bridge — probe stdio MCP servers from Hermes/OpenClaw configs."""

from __future__ import annotations

import asyncio
import logging
import shutil
from typing import Any

from alpha_os.integrations.mcp_discovery import (
    config_paths_status,
    discover_mcp_servers,
    discovery_sources,
)

logger = logging.getLogger("alpha_os.mcp")


def _command_preview(command: str, args: list[str]) -> str:
    parts = [command, *args]
    return " ".join(parts)[:160]


def _mcp_package_missing() -> str:
    return "mcp package not installed — run: pip install alpha-os[mcp]"


class MCPBridge:
    """Single stdio MCP server — same subprocess Hermes/OpenClaw would launch."""

    def __init__(self, definition: dict[str, Any]):
        self.definition = definition
        self.name = str(definition.get("name", ""))
        self.command = str(definition.get("command") or "")
        self.args = list(definition.get("args") or [])
        self._env = dict(definition.get("env") or {})
        self.env_keys = list(definition.get("env_keys") or sorted(self._env.keys()))
        self.source = str(definition.get("source") or "")
        self.config_path = str(definition.get("config_path") or "")
        self.transport = str(definition.get("transport") or "stdio")
        self.probeable = bool(definition.get("probeable", True))
        self.connect_timeout = float(definition.get("connect_timeout") or 8.0)
        self.tool_policy = dict(definition.get("tool_policy") or {})
        self._connected = False
        self._tools: list[dict[str, Any]] = []
        self._error: str | None = None

    async def connect(self) -> bool:
        if not self.probeable:
            self._error = None
            self._connected = False
            self._tools = []
            return False

        if not self.command:
            self._error = "Missing command"
            return False

        if not shutil.which(self.command.split("/")[-1]) and "/" not in self.command:
            # npx, uvx, etc. may not be in PATH during probe — still try
            pass

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            self._error = _mcp_package_missing()
            return False

        import os

        env = {**dict(os.environ), **{k: str(v) for k, v in self._env.items()}}
        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=env,
        )
        timeout = self.connect_timeout
        try:
            async with asyncio.timeout(timeout):
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        self._tools = [
                            {
                                "name": t.name,
                                "description": (t.description or "")[:200],
                            }
                            for t in (result.tools or [])
                        ]
                        self._connected = True
                        self._error = None
                        return True
        except Exception as e:
            logger.warning("MCP %s offline: %s", self.name, e)
            self._connected = False
            self._error = str(e)[:240]
            self._tools = []
            return False

    def get_tools(self) -> list[dict[str, Any]]:
        return list(self._tools)

    def to_dict(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "name": self.name,
            "connected": self._connected,
            "transport": self.transport,
            "probeable": self.probeable,
            "tool_count": len(self._tools),
            "tools": self._tools[:24],
            "error": self._error,
            "source": self.source,
            "config_path": self.config_path,
            "tool_policy": self.tool_policy or None,
        }
        if self.probeable:
            base["command"] = self.command
            base["args"] = self.args
            base["command_preview"] = _command_preview(self.command, self.args)
            if self.env_keys:
                base["env_keys"] = self.env_keys
        else:
            base["url"] = self.definition.get("url")
            base["auth"] = self.definition.get("auth")
            base["note"] = self.definition.get("note")
            base["status"] = "configured"
        return base


class MCPRegistry:
    """Discover and probe stdio MCP servers from runtime configs."""

    def __init__(self):
        self._servers: list[MCPBridge] = []
        self._last_scan: float | None = None
        self._runtime: str = "auto"
        self._data: dict[str, Any] = self._empty_data()

    @staticmethod
    def _empty_data() -> dict[str, Any]:
        return {
            "connected": False,
            "server_count": 0,
            "stdio_count": 0,
            "remote_count": 0,
            "tool_count": 0,
            "servers": [],
            "config_paths": [],
            "sources": [],
            "runtime": "auto",
            "error": None,
            "summary": (
                "No MCP servers in runtime config — add stdio servers to "
                "mcp_servers (Hermes) or mcp.servers (OpenClaw)"
            ),
        }

    def _load_definitions(self, runtime: str | None = None) -> list[MCPBridge]:
        defs = discover_mcp_servers(runtime)
        return [MCPBridge(d) for d in defs]

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

    async def refresh(self, runtime: str | None = None) -> dict[str, Any]:
        import time

        self._runtime = (runtime or self._runtime or "auto").lower()
        self._servers = self._load_definitions(self._runtime)
        config_paths = config_paths_status()

        if not self._servers:
            self._data = {
                **self._empty_data(),
                "runtime": self._runtime,
                "config_paths": config_paths,
                "sources": discovery_sources(),
                "error": self._empty_message(self._runtime),
                "summary": self._empty_message(self._runtime),
            }
            self._last_scan = time.time()
            return dict(self._data)

        stdio = [s for s in self._servers if s.probeable]
        remote = [s for s in self._servers if not s.probeable]

        if stdio:
            results = await asyncio.gather(
                *[s.connect() for s in stdio],
                return_exceptions=True,
            )
            for bridge, res in zip(stdio, results):
                if isinstance(res, Exception):
                    bridge._error = str(res)[:240]

        servers_out = [s.to_dict() for s in self._servers]
        stdio_connected = sum(1 for s in stdio if s._connected)
        total_tools = sum(len(s.get_tools()) for s in stdio)
        any_stdio_ok = stdio_connected > 0

        if not stdio and remote:
            summary = (
                f"{len(remote)} remote MCP server(s) configured — "
                "connections managed by Hermes/OpenClaw"
            )
            error = None
        elif stdio and not any_stdio_ok:
            summary = f"0/{len(stdio)} stdio MCP server(s) reachable"
            error = "All stdio MCP probes failed — check command, args, and env in runtime config"
        else:
            remote_note = f", {len(remote)} remote" if remote else ""
            summary = (
                f"{stdio_connected}/{len(stdio)} stdio MCP online"
                f"{remote_note} · {total_tools} tools discovered"
            )
            error = None if any_stdio_ok or remote else summary

        self._data = {
            "connected": any_stdio_ok or bool(remote),
            "server_count": len(self._servers),
            "stdio_count": len(stdio),
            "remote_count": len(remote),
            "tool_count": total_tools,
            "servers": servers_out,
            "config_paths": config_paths,
            "sources": discovery_sources(),
            "runtime": self._runtime,
            "error": error,
            "summary": summary,
        }
        self._last_scan = time.time()
        return dict(self._data)

    def get_panel_data(self) -> dict[str, Any]:
        return dict(self._data)