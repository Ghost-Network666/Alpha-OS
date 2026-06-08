"""Auto-detect ~/.hermes / ~/.openclaw and sync into ~/.alpha-os/config.yaml."""

from __future__ import annotations

import logging
from typing import Any

from alpha_os.bridges.detector import RuntimeInfo, detect_best, detect_hermes, detect_openclaw
from alpha_os.config import active_hermes_profile, hermes_home, load_config, save_config
from alpha_os.runtime_env import active_runtime_choice, openclaw_home

logger = logging.getLogger("alpha_os.runtime_sync")


def _apply_hermes(
    cfg: dict[str, Any],
    info: RuntimeInfo,
    *,
    only_missing: bool = False,
) -> None:
    if not hermes_home().exists():
        return
    block = cfg.setdefault("hermes", {})
    if info.gateway_url and (not only_missing or not block.get("gateway_url")):
        block["gateway_url"] = info.gateway_url
    if info.api_key and (not only_missing or not block.get("api_key")):
        block["api_key"] = info.api_key
    block["profile"] = active_hermes_profile()
    block["home"] = str(hermes_home())
    block["connected"] = info.connected
    if info.details:
        block["detect"] = info.details


def _apply_openclaw(
    cfg: dict[str, Any],
    info: RuntimeInfo,
    *,
    only_missing: bool = False,
) -> None:
    if not openclaw_home().exists():
        return
    block = cfg.setdefault("openclaw", {})
    ws = info.ws_url or (
        info.gateway_url.replace("http://", "ws://").replace("https://", "wss://")
        if info.gateway_url
        else ""
    )
    if ws and (not only_missing or not block.get("ws_url")):
        block["ws_url"] = ws
    if info.api_key and (not only_missing or not block.get("token")):
        block["token"] = info.api_key
    block["home"] = str(openclaw_home())
    block["connected"] = info.connected
    if info.details:
        block["detect"] = info.details


async def sync_runtime_config(
    *,
    sync_voice: bool = True,
    only_missing: bool = False,
) -> dict[str, Any]:
    """Probe local Hermes/OpenClaw homes and mirror settings into Alpha OS config."""
    import asyncio

    hermes, openclaw, best = await asyncio.gather(
        detect_hermes(),
        detect_openclaw(),
        detect_best(),
    )

    cfg = load_config()
    env_runtime = active_runtime_choice()
    runtime_pref = (
        env_runtime
        if env_runtime in ("hermes", "openclaw")
        else str(cfg.get("runtime", "auto")).lower()
    )

    _apply_hermes(cfg, hermes, only_missing=only_missing)
    _apply_openclaw(cfg, openclaw, only_missing=only_missing)

    if runtime_pref == "auto":
        if best.name != "offline":
            cfg["runtime"] = best.name
        elif hermes_home().exists():
            cfg["runtime"] = "hermes"
        elif openclaw_home().exists():
            cfg["runtime"] = "openclaw"
    elif runtime_pref == "hermes" and hermes_home().exists():
        cfg["runtime"] = "hermes"
    elif runtime_pref == "openclaw" and openclaw_home().exists():
        cfg["runtime"] = "openclaw"

    save_config(cfg)
    logger.info(
        "Runtime sync — hermes=%s openclaw=%s active=%s only_missing=%s",
        "live" if hermes.connected else "offline",
        "live" if openclaw.connected else "offline",
        cfg.get("runtime"),
        only_missing,
    )

    voice: dict[str, Any] | None = None
    if sync_voice and hermes_home().exists() and not only_missing:
        try:
            from alpha_os.voice.hermes_sync import sync_voice_to_alpha_os

            voice = sync_voice_to_alpha_os()
        except Exception as exc:
            logger.warning("Voice sync skipped: %s", exc)

    return {
        "runtime": cfg.get("runtime"),
        "best": best.name,
        "hermes_connected": hermes.connected,
        "openclaw_connected": openclaw.connected,
        "hermes_gateway_url": hermes.gateway_url,
        "openclaw_ws_url": openclaw.ws_url or openclaw.gateway_url,
        "hermes_profile": active_hermes_profile(),
        "voice": voice,
    }