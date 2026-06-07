"""Detect Grok voice via Hermes/OpenClaw X OAuth (SuperGrok) — not xAI API keys."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from alpha_os.config import read_openclaw_config

logger = logging.getLogger("alpha_os.voice")

_OPENCLAW_HOME = Path.home() / ".openclaw"
_HERMES_HOME = Path.home() / ".hermes"


def _walk(obj: Any) -> list[Any]:
    if isinstance(obj, dict):
        out = [obj]
        for v in obj.values():
            out.extend(_walk(v))
        return out
    if isinstance(obj, list):
        out: list[Any] = []
        for item in obj:
            out.extend(_walk(item))
        return out
    return []


def _blob_has_xai_oauth(blob: Any) -> bool:
    for node in _walk(blob):
        if not isinstance(node, dict):
            continue
        provider = str(
            node.get("provider")
            or node.get("providerId")
            or node.get("provider_id")
            or ""
        ).lower()
        mode = str(node.get("mode") or node.get("auth") or node.get("type") or "").lower()
        if provider in {"xai", "grok", "grok-sso", "xai-grok-auth"} and mode in {
            "oauth",
            "device_code",
            "device-code",
            "sso",
        }:
            return True
        if provider in {"xai", "grok"} and any(
            k in node for k in ("access", "accessToken", "refreshToken", "token", "oauth")
        ):
            return True
    return False


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def openclaw_grok_oauth_configured() -> bool:
    cfg = read_openclaw_config()
    plugins = cfg.get("plugins", {}) if isinstance(cfg.get("plugins"), dict) else {}
    entries = plugins.get("entries", {}) if isinstance(plugins.get("entries"), dict) else {}
    xai_plugin = entries.get("xai", {}) if isinstance(entries.get("xai"), dict) else {}
    if xai_plugin.get("enabled", True) and isinstance(xai_plugin.get("config"), dict):
        if _blob_has_xai_oauth(xai_plugin):
            return True

    agents = cfg.get("agents", {}) if isinstance(cfg.get("agents"), dict) else {}
    defaults = agents.get("defaults", {}) if isinstance(agents.get("defaults"), dict) else {}
    model = defaults.get("model", {}) if isinstance(defaults.get("model"), dict) else {}
    primary = str(model.get("primary") or "")
    if primary.startswith("xai/") or primary.startswith("grok"):
        return True

    candidates: list[Path] = []
    agents_dir = _OPENCLAW_HOME / "agents"
    if agents_dir.is_dir():
        candidates.extend(agents_dir.glob("**/auth-profiles.json"))
        candidates.extend(agents_dir.glob("**/auth.json"))
    cred_dir = _OPENCLAW_HOME / "credentials"
    if cred_dir.is_dir():
        candidates.extend(cred_dir.glob("**/*.json"))

    for path in candidates:
        data = _read_json(path)
        if data and _blob_has_xai_oauth(data):
            return True

    return False


def hermes_installed() -> bool:
    return _HERMES_HOME.is_dir()


def grok_via_runtime_oauth(
    *,
    hermes_connected: bool = False,
    openclaw_connected: bool = False,
    runtime: str = "offline",
) -> bool:
    """Grok voice is available through the user's Hermes/OpenClaw OAuth session."""
    if openclaw_connected and openclaw_grok_oauth_configured():
        return True
    if runtime == "openclaw" and openclaw_grok_oauth_configured():
        return True
    if hermes_connected and hermes_installed():
        return True
    if runtime == "hermes" and hermes_installed():
        return True
    return False