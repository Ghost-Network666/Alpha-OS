"""Hermes profile agent configuration for Alpha OS settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alpha_os.config import (
    active_hermes_profile,
    hermes_home,
    list_hermes_profiles,
    read_hermes_profile_config,
    write_hermes_config,
)


def _model_block(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("model")
    return block if isinstance(block, dict) else {}


def _agent_block(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("agent")
    return block if isinstance(block, dict) else {}


def _mcp_block(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("mcp_servers")
    return block if isinstance(block, dict) else {}


def _toolsets_list(cfg: dict[str, Any]) -> list[str]:
    raw = cfg.get("toolsets")
    if not isinstance(raw, list):
        return []
    return [str(t) for t in raw if t]


def _skills_for_profile(profile: str) -> list[dict[str, str]]:
    root = hermes_home() / "profiles" / profile / "skills"
    if not root.is_dir():
        return []
    out: list[dict[str, str]] = []
    for path in sorted(root.rglob("SKILL.md")):
        rel = path.relative_to(root)
        skill_dir = str(rel.parent).replace("\\", "/")
        if skill_dir == ".":
            skill_dir = path.parent.name
        out.append(
            {
                "id": skill_dir,
                "name": skill_dir.split("/")[-1],
                "path": str(path),
                "rel_path": str(rel).replace("\\", "/"),
            }
        )
    return out


def profile_summary(name: str) -> dict[str, Any]:
    cfg = read_hermes_profile_config(name)
    model = _model_block(cfg)
    agent = _agent_block(cfg)
    mcp = _mcp_block(cfg)
    disabled = agent.get("disabled_toolsets")
    disabled_set = {str(x) for x in disabled} if isinstance(disabled, list) else set()
    toolsets = _toolsets_list(cfg)
    mcp_servers: list[dict[str, Any]] = []
    for server_id, block in mcp.items():
        if not isinstance(block, dict):
            continue
        mcp_servers.append(
            {
                "id": str(server_id),
                "enabled": bool(block.get("enabled", True)),
                "command": str(block.get("command") or ""),
            }
        )
    return {
        "name": name,
        "active": name == active_hermes_profile(),
        "config_path": str(hermes_home() / "profiles" / name / "config.yaml"),
        "model": {
            "provider": str(model.get("provider") or ""),
            "default": str(model.get("default") or ""),
            "base_url": str(model.get("base_url") or ""),
        },
        "toolsets": [
            {"id": t, "enabled": t not in disabled_set}
            for t in toolsets
        ],
        "mcp_servers": mcp_servers,
        "skills": _skills_for_profile(name),
        "disabled_toolsets": sorted(disabled_set),
    }


def list_profile_summaries() -> list[dict[str, Any]]:
    return [profile_summary(name) for name in list_hermes_profiles()]


def read_skill_markdown(profile: str, rel_path: str) -> dict[str, Any]:
    root = hermes_home() / "profiles" / profile / "skills"
    safe = Path(rel_path.replace("\\", "/").lstrip("/"))
    if ".." in safe.parts:
        return {"ok": False, "error": "Invalid path"}
    path = (root / safe).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return {"ok": False, "error": "Path outside skills directory"}
    if not path.is_file():
        return {"ok": False, "error": "Skill file not found"}
    try:
        return {"ok": True, "path": str(path), "content": path.read_text(encoding="utf-8")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def apply_profile_agent_config(
    profile: str,
    *,
    model_provider: str | None = None,
    model_default: str | None = None,
    disabled_toolsets: list[str] | None = None,
    mcp_enabled: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Update agent model, toolsets, and MCP toggles for a Hermes profile."""
    name = (profile or "").strip() or active_hermes_profile()
    cfg = read_hermes_profile_config(name)
    if not cfg:
        cfg = {}

    model = dict(_model_block(cfg))
    if model_provider is not None:
        model["provider"] = model_provider.strip()
    if model_default is not None:
        model["default"] = model_default.strip()
    if model:
        cfg["model"] = model

    if disabled_toolsets is not None:
        agent = dict(_agent_block(cfg))
        agent["disabled_toolsets"] = list(disabled_toolsets)
        cfg["agent"] = agent

    if mcp_enabled:
        mcp = dict(_mcp_block(cfg))
        for server_id, enabled in mcp_enabled.items():
            block = mcp.get(server_id)
            if isinstance(block, dict):
                updated = dict(block)
                updated["enabled"] = bool(enabled)
                mcp[server_id] = updated
        cfg["mcp_servers"] = mcp

    write_hermes_config(cfg, profile=name)
    return profile_summary(name)