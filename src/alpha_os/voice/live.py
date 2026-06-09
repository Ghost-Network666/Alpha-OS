"""Build live voice status payload for dashboard and API."""

from __future__ import annotations

from typing import Any

from alpha_os.voice.hermes_sync import load_voice_config
from alpha_os.voice.labels import (
    is_local_stt,
    is_local_tts,
    stt_provider_label,
    tts_provider_label,
)
from alpha_os.voice.usage import voice_usage_session


def build_voice_live(*, hermes_profile: str | None = None) -> dict[str, Any]:
    cfg = load_voice_config(profile=hermes_profile)
    tts = str(cfg.get("tts_provider") or "edge").lower()
    stt = str(cfg.get("stt_provider") or "local").lower()
    session = voice_usage_session().to_dict()

    return {
        "active": bool(cfg.get("browser_wake", True)) or bool(cfg.get("server_wake")),
        "auto_tts": bool(cfg.get("auto_tts", True)),
        "stt_enabled": bool(cfg.get("stt_enabled", True)),
        "tts_provider": tts,
        "tts_provider_label": tts_provider_label(tts),
        "tts_voice": str(cfg.get("tts_voice") or ""),
        "tts_model": str(cfg.get("tts_model") or ""),
        "tts_local": is_local_tts(tts),
        "stt_provider": stt,
        "stt_provider_label": stt_provider_label(stt),
        "stt_model": str(cfg.get("stt_model") or ""),
        "stt_local": is_local_stt(stt),
        "wake_word": str(cfg.get("wake_word") or "hey alpha"),
        "hermes_profile": cfg.get("hermes_profile"),
        "session": session,
    }