"""Discover MCP servers from Hermes and OpenClaw runtime configs.

Alpha OS reads the same stdio (and remote) MCP definitions that Hermes Agent and
OpenClaw use — it does not maintain a separate MCP registry.

Hermes:  ~/.hermes/config.yaml  →  mcp_servers
OpenClaw: ~/.openclaw/openclaw.json  →  mcp.servers
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("alpha_os.mcp.discovery")

from alpha_os.config import hermes_home
from alpha_os.runtime_env import openclaw_home

HERMES_HOME = hermes_home()
OPENCLAW_HOME = openclaw_home()

HERMES_CONFIG_PATHS = (
    HERMES_HOME / "config.yaml",
    HERMES_HOME / "config.yml",
)

OPENCLAW_CONFIG_PATHS = (
    OPENCLAW_HOME / "openclaw.json",
    OPENCLAW_HOME / "clawdbot.json",
    OPENCLAW_HOME / "moltbot.json",
)


def _is_disabled(raw: dict[str, Any]) -> bool:
    return raw.get("enabled") is False


def _tool_policy(raw: dict[str, Any]) -> dict[str, Any]:
    tools = raw.get("tools")
    tool_filter = raw.get("toolFilter")
    policy: dict[str, Any] = {}
    if isinstance(tools, dict):
        if tools.get("include"):
            policy["include"] = tools["include"]
        if tools.get("exclude"):
            policy["exclude"] = tools["exclude"]
    if isinstance(tool_filter, dict):
        if tool_filter.get("include"):
            policy["include"] = tool_filter["include"]
        if tool_filter.get("exclude"):
            policy["exclude"] = tool_filter["exclude"]
    return policy


def _normalize_stdio_entry(
    name: str,
    raw: dict[str, Any],
    source: str,
    config_path: str,
) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if _is_disabled(raw):
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
        "probeable": True,
        "command": str(cmd),
        "args": [str(a) for a in args],
        "env": {str(k): str(v) for k, v in env.items()},
        "env_keys": sorted(str(k) for k in env.keys()),
        "source": source,
        "config_path": config_path,
        "tool_policy": _tool_policy(raw),
        "connect_timeout": _connect_timeout(raw),
    }


def _normalize_remote_entry(
    name: str,
    raw: dict[str, Any],
    source: str,
    config_path: str,
) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if _is_disabled(raw):
        return None
    url = raw.get("url")
    if not url:
        return None
    transport = str(
        raw.get("transport")
        or raw.get("type")
        or ("sse" if str(url).rstrip("/").endswith("/sse") else "streamable-http")
    ).lower()
    if transport == "http":
        transport = "streamable-http"
    return {
        "name": name,
        "transport": transport,
        "probeable": False,
        "url": str(url),
        "auth": str(raw.get("auth") or "") or None,
        "source": source,
        "config_path": config_path,
        "tool_policy": _tool_policy(raw),
        "note": (
            "Remote MCP — managed by your runtime (OAuth/TLS). "
            "Alpha OS lists it from config; Hermes/OpenClaw run the connection."
        ),
    }


def _connect_timeout(raw: dict[str, Any]) -> float:
    for key in ("connect_timeout", "connectTimeout", "connectionTimeoutMs"):
        val = raw.get(key)
        if val is None:
            continue
        try:
            timeout = float(val)
            if key.endswith("Ms"):
                timeout /= 1000.0
            return max(2.0, min(timeout, 30.0))
        except (TypeError, ValueError):
            continue
    return 8.0


def _parse_server_block(
    servers: dict[str, Any],
    source: str,
    config_path: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        if _is_disabled(cfg):
            continue
        if cfg.get("command"):
            entry = _normalize_stdio_entry(name, cfg, source, config_path)
        elif cfg.get("url"):
            entry = _normalize_remote_entry(name, cfg, source, config_path)
        else:
            continue
        if entry:
            out.append(entry)
    return out


def _parse_hermes_config() -> list[dict[str, Any]]:
    try:
        import yaml
    except ImportError:
        return []

    seen_paths: set[str] = set()
    for path in HERMES_CONFIG_PATHS:
        key = str(path)
        if key in seen_paths or not path.exists():
            continue
        seen_paths.add(key)
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except Exception as e:
            logger.debug("Could not parse %s: %s", path, e)
            continue
        if not isinstance(data, dict):
            continue
        block = data.get("mcp_servers") or data.get("mcpServers")
        if isinstance(block, dict):
            entries = _parse_server_block(block, "hermes", str(path))
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
    return _parse_server_block(servers, "openclaw", str(path))


def _runtime_sources(runtime: str | None) -> list[str]:
    runtime = (runtime or "auto").lower()
    if runtime == "hermes":
        return ["hermes"]
    if runtime == "openclaw":
        return ["openclaw"]
    return ["hermes", "openclaw"]


def discover_mcp_servers(runtime: str | None = None) -> list[dict[str, Any]]:
    """
    Return MCP server definitions from the active runtime config(s).

    Stdio entries are probeable by Alpha OS. Remote HTTP/SSE entries are listed
    for visibility — Hermes/OpenClaw own those connections.
    """
    allowed = set(_runtime_sources(runtime))
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    def _merge(entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            if entry.get("source") not in allowed:
                continue
            name = entry["name"]
            if name in seen:
                continue
            seen.add(name)
            out.append(entry)

    if "hermes" in allowed:
        _merge(_parse_hermes_config())

    if "openclaw" in allowed:
        for path in OPENCLAW_CONFIG_PATHS:
            _merge(_parse_openclaw_config(path))

    override = os.getenv("ALPHA_MCP_CONFIG", "").strip()
    if override:
        p = Path(override)
        if p.exists():
            try:
                import yaml

                raw = (
                    yaml.safe_load(p.read_text())
                    if p.suffix in (".yaml", ".yml")
                    else json.loads(p.read_text())
                )
                if isinstance(raw, dict):
                    block = raw.get("mcp_servers") or raw.get("mcpServers")
                    if isinstance(block, dict):
                        _merge(_parse_server_block(block, "override", str(p)))
            except Exception as e:
                logger.debug("ALPHA_MCP_CONFIG parse failed: %s", e)

    return out


def config_paths_status() -> list[dict[str, Any]]:
    """Config files Alpha OS reads for MCP definitions."""
    rows: list[dict[str, Any]] = []
    for path in HERMES_CONFIG_PATHS:
        rows.append(
            {
                "runtime": "hermes",
                "path": str(path),
                "exists": path.exists(),
                "key": "mcp_servers",
            }
        )
        if path.exists():
            break
    for path in OPENCLAW_CONFIG_PATHS:
        rows.append(
            {
                "runtime": "openclaw",
                "path": str(path),
                "exists": path.exists(),
                "key": "mcp.servers",
            }
        )
        if path.exists():
            break
    override = os.getenv("ALPHA_MCP_CONFIG", "").strip()
    if override:
        p = Path(override)
        rows.append(
            {
                "runtime": "override",
                "path": str(p),
                "exists": p.exists(),
                "key": "mcp_servers",
            }
        )
    return rows


def discovery_sources() -> list[str]:
    """Paths Alpha OS checks for MCP definitions."""
    return [r["path"] for r in config_paths_status()]