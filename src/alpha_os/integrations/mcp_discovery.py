"""Discover MCP server definitions from user config files."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("alpha_os.mcp.discovery")

CURSOR_KEYS = ("mcpServers", "mcp_servers")


def _normalize_entry(name: str, raw: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("url"):
        return {
            "name": name,
            "transport": "http",
            "url": raw["url"],
            "command": None,
            "args": [],
            "env": raw.get("env") or {},
        }
    cmd = raw.get("command")
    if not cmd:
        return None
    args = raw.get("args") or []
    if not isinstance(args, list):
        args = [str(args)]
    return {
        "name": name,
        "transport": "stdio",
        "url": None,
        "command": str(cmd),
        "args": [str(a) for a in args],
        "env": raw.get("env") or {},
    }


def _parse_openclaw_config(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    mcp = data.get("mcp")
    if not isinstance(mcp, dict):
        return []
    servers = mcp.get("servers")
    if not isinstance(servers, dict):
        return []
    out: list[dict[str, Any]] = []
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        entry = _normalize_entry(name, cfg)
        if entry:
            entry["source"] = "openclaw"
            out.append(entry)
    return out


def _parse_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        logger.debug("Could not parse %s: %s", path, e)
        return []
    servers: list[dict[str, Any]] = []
    if isinstance(data, dict):
        for key in CURSOR_KEYS:
            block = data.get(key)
            if isinstance(block, dict):
                for name, cfg in block.items():
                    entry = _normalize_entry(name, cfg)
                    if entry:
                        servers.append(entry)
    return servers


def discover_mcp_servers() -> list[dict[str, Any]]:
    """Return merged MCP server definitions from known config locations."""
    home = Path.home()
    paths = [
        Path(os.getenv("ALPHA_MCP_CONFIG", "")),
        home / ".alpha-os" / "mcp.json",
        home / ".hermes" / "mcp.json",
        home / ".cursor" / "mcp.json",
        home / ".config" / "cursor" / "mcp.json",
    ]
    openclaw_paths = [
        home / ".openclaw" / "openclaw.json",
        home / ".openclaw" / "clawdbot.json",
        home / ".openclaw" / "moltbot.json",
    ]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for path in paths:
        if not path or not str(path):
            continue
        for entry in _parse_file(path):
            name = entry["name"]
            if name in seen:
                continue
            seen.add(name)
            out.append(entry)
    for path in openclaw_paths:
        for entry in _parse_openclaw_config(path):
            name = entry["name"]
            if name in seen:
                continue
            seen.add(name)
            out.append(entry)
    return out