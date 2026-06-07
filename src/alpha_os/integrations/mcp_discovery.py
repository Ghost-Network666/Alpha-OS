"""Discover stdio MCP servers from Hermes and OpenClaw runtime configs."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("alpha_os.mcp.discovery")

HERMES_HOME = Path.home() / ".hermes"
OPENCLAW_HOME = Path.home() / ".openclaw"


def _normalize_stdio_entry(
    name: str,
    raw: dict[str, Any],
    source: str,
) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("enabled") is False:
        return None
    cmd = raw.get("command")
    if not cmd:
        return None
    args = raw.get("args") or []
    if not isinstance(args, list):
        args = [str(args)]
    env = raw.get("env") or {}
    if not isinstance(env, dict):
        env = {}
    return {
        "name": name,
        "transport": "stdio",
        "command": str(cmd),
        "args": [str(a) for a in args],
        "env": {str(k): str(v) for k, v in env.items()},
        "source": source,
    }


def _parse_server_block(
    servers: dict[str, Any],
    source: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        entry = _normalize_stdio_entry(name, cfg, source)
        if entry:
            out.append(entry)
    return out


def _parse_hermes_config() -> list[dict[str, Any]]:
    """Hermes stores MCP in ~/.hermes/config.yaml under mcp_servers."""
    try:
        import yaml
    except ImportError:
        return []

    for path in (HERMES_HOME / "config.yaml", HERMES_HOME / "config.yml"):
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except Exception as e:
            logger.debug("Could not parse %s: %s", path, e)
            continue
        if not isinstance(data, dict):
            continue
        block = data.get("mcp_servers") or data.get("mcpServers")
        if isinstance(block, dict):
            entries = _parse_server_block(block, "hermes")
            if entries:
                return entries
    return []


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
    return _parse_server_block(servers, "openclaw")


def discover_mcp_servers() -> list[dict[str, Any]]:
    """
    Return stdio MCP server definitions from Hermes + OpenClaw configs.
    Hermes: ~/.hermes/config.yaml → mcp_servers
    OpenClaw: ~/.openclaw/openclaw.json → mcp.servers
    """
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    def _merge(entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            name = entry["name"]
            if name in seen:
                continue
            seen.add(name)
            out.append(entry)

    _merge(_parse_hermes_config())

    for path in (
        OPENCLAW_HOME / "openclaw.json",
        OPENCLAW_HOME / "clawdbot.json",
        OPENCLAW_HOME / "moltbot.json",
    ):
        _merge(_parse_openclaw_config(path))

    override = os.getenv("ALPHA_MCP_CONFIG", "").strip()
    if override:
        p = Path(override)
        if p.exists():
            try:
                import yaml

                raw = yaml.safe_load(p.read_text()) if p.suffix in (".yaml", ".yml") else json.loads(p.read_text())
                if isinstance(raw, dict):
                    block = raw.get("mcp_servers") or raw.get("mcpServers")
                    if isinstance(block, dict):
                        _merge(_parse_server_block(block, "override"))
            except Exception as e:
                logger.debug("ALPHA_MCP_CONFIG parse failed: %s", e)

    return out


def discovery_sources() -> list[str]:
    """Paths Alpha OS checks for stdio MCP definitions."""
    sources = [
        str(HERMES_HOME / "config.yaml"),
        str(OPENCLAW_HOME / "openclaw.json"),
    ]
    override = os.getenv("ALPHA_MCP_CONFIG", "").strip()
    if override:
        sources.append(override)
    return sources