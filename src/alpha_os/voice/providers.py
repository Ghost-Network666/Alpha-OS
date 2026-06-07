"""Voice provider discovery — only reports real availability, never fake status."""

from __future__ import annotations

import os
import shutil
from typing import Any

from alpha_os.config import get


def _has_env(*keys: str) -> bool:
    return any(os.getenv(k, "").strip() for k in keys)


def get_voice_providers() -> list[dict[str, Any]]:
    """Return provider cards for the settings panel."""
    providers: list[dict[str, Any]] = []

    providers.append({
        "id": "browser",
        "label": "Browser Web Speech",
        "kind": "stt",
        "available": True,
        "enabled": True,
        "note": "Chrome/Edge mic button in dashboard",
    })

    server_available = False
    try:
        import speech_recognition  # noqa: F401
        server_available = True
    except ImportError:
        pass

    providers.append({
        "id": "server_mic",
        "label": "Server microphone",
        "kind": "stt",
        "available": server_available,
        "enabled": bool(get("voice.enabled", False)) and server_available,
        "note": "pip install 'alpha-os[voice]' && alpha-os serve --voice"
        if not server_available
        else "alpha-os serve --voice",
    })

    if _has_env("DEEPGRAM_API_KEY"):
        providers.append({
            "id": "deepgram",
            "label": "Deepgram",
            "kind": "stt",
            "available": True,
            "enabled": bool(get("voice.providers.deepgram", False)),
            "note": "DEEPGRAM_API_KEY detected",
        })

    if _has_env("ELEVENLABS_API_KEY", "XI_API_KEY"):
        providers.append({
            "id": "elevenlabs",
            "label": "ElevenLabs",
            "kind": "tts",
            "available": True,
            "enabled": bool(get("voice.providers.elevenlabs", False)),
            "note": "API key detected in environment",
        })

    if _has_env("OPENAI_API_KEY"):
        providers.append({
            "id": "openai_realtime",
            "label": "OpenAI Realtime",
            "kind": "sts",
            "available": True,
            "enabled": bool(get("voice.providers.openai_realtime", False)),
            "note": "OPENAI_API_KEY detected — route via Hermes/OpenClaw Talk",
        })

    if shutil.which("whisper") or shutil.which("faster-whisper"):
        providers.append({
            "id": "faster_whisper",
            "label": "Faster-Whisper (local)",
            "kind": "stt",
            "available": True,
            "enabled": bool(get("voice.providers.faster_whisper", False)),
            "note": "Local whisper binary found on PATH",
        })

    return providers