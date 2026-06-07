"""Voice provider discovery — Hermes/OpenClaw Grok OAuth only (no xAI API keys)."""

from __future__ import annotations

from typing import Any

from alpha_os.voice.grok_oauth import grok_via_runtime_oauth, hermes_installed, openclaw_grok_oauth_configured
from alpha_os.voice.hermes_sync import load_voice_config


def get_voice_providers(
    *,
    hermes_connected: bool = False,
    openclaw_connected: bool = False,
    runtime: str = "offline",
) -> list[dict[str, Any]]:
    """Return provider cards for the settings panel."""
    providers: list[dict[str, Any]] = []
    voice_cfg = load_voice_config()
    grok_oauth = grok_via_runtime_oauth(
        hermes_connected=hermes_connected,
        openclaw_connected=openclaw_connected,
        runtime=runtime,
    )

    providers.append({
        "id": "wake_phrase",
        "label": "Wake phrase (“hey alpha”)",
        "kind": "wake",
        "available": True,
        "enabled": True,
        "note": "Always-on phrase detection — no button, no API keys",
    })

    providers.append({
        "id": "hermes_gateway",
        "label": "Hermes gateway",
        "kind": "relay",
        "available": hermes_installed(),
        "enabled": hermes_connected or runtime == "hermes",
        "note": "Commands relay to the user's Hermes server when connected",
    })

    providers.append({
        "id": "grok_oauth",
        "label": "Grok (X OAuth / SuperGrok)",
        "kind": "sts",
        "available": grok_oauth,
        "enabled": grok_oauth and bool(voice_cfg.get("grok_oauth", True)),
        "note": (
            "Uses X OAuth / SuperGrok via Hermes or OpenClaw — not xAI API keys"
            if grok_oauth
            else "Sign in with X OAuth in OpenClaw (openclaw models auth login --provider xai) "
            "or connect Hermes with Grok configured"
        ),
    })

    if openclaw_grok_oauth_configured():
        providers.append({
            "id": "openclaw_xai",
            "label": "OpenClaw xAI OAuth",
            "kind": "auth",
            "available": True,
            "enabled": openclaw_connected or runtime == "openclaw",
            "note": "Grok models authenticated via OpenClaw OAuth profile",
        })

    server_wake = False
    try:
        import speech_recognition  # noqa: F401

        server_wake = True
    except ImportError:
        pass

    providers.append({
        "id": "server_wake",
        "label": "Server wake listener",
        "kind": "wake",
        "available": server_wake,
        "enabled": bool(voice_cfg.get("server_wake", False)) and server_wake,
        "note": "pip install 'alpha-os[voice]' && alpha-os serve --voice"
        if not server_wake
        else "Server mic listens for “hey alpha”, relays via Hermes",
    })

    return providers