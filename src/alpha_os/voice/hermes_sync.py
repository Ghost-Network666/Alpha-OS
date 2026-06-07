"""Sync Alpha OS voice settings with ~/.hermes/config.yaml."""

from __future__ import annotations

from typing import Any

from alpha_os.config import (
    get,
    hermes_config_path,
    read_hermes_config,
    set_key,
    write_hermes_config,
)

DEFAULT_WAKE = "hey alpha"

VOICE_DEFAULTS: dict[str, Any] = {
    "wake_word": DEFAULT_WAKE,
    "browser_wake": True,
    "server_wake": False,
    "record_key": "ctrl+b",
    "max_recording_seconds": 120,
    "auto_tts": True,
    "beep_enabled": True,
    "silence_threshold": 200,
    "silence_duration": 3.0,
    "stt_provider": "local",
    "stt_model": "base",
    "stt_enabled": True,
    "tts_provider": "edge",
    "tts_voice": "en-US-AriaNeural",
    "grok_oauth": True,
}


def _alpha_os_block(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("alpha_os")
    return block if isinstance(block, dict) else {}


def _voice_block(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("voice")
    return block if isinstance(block, dict) else {}


def _stt_block(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("stt")
    return block if isinstance(block, dict) else {}


def _tts_block(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("tts")
    return block if isinstance(block, dict) else {}


def load_voice_config() -> dict[str, Any]:
    """Effective voice config: Hermes yaml + Alpha OS overrides."""
    out = dict(VOICE_DEFAULTS)
    try:
        from alpha_os.voice.openclaw_voicewake import load_wake_word_from_openclaw

        oc_wake = load_wake_word_from_openclaw(out["wake_word"])
        if oc_wake:
            out["wake_word"] = oc_wake
    except Exception:
        pass
    hermes = read_hermes_config()
    alpha = _alpha_os_block(hermes)
    voice = _voice_block(hermes)
    stt = _stt_block(hermes)
    tts = _tts_block(hermes)

    if alpha.get("wake_word"):
        out["wake_word"] = str(alpha["wake_word"]).strip()
    if "browser_wake" in alpha:
        out["browser_wake"] = bool(alpha["browser_wake"])
    if "server_wake" in alpha:
        out["server_wake"] = bool(alpha["server_wake"])
    if "grok_oauth" in alpha:
        out["grok_oauth"] = bool(alpha["grok_oauth"])

    for key in (
        "record_key",
        "max_recording_seconds",
        "auto_tts",
        "beep_enabled",
        "silence_threshold",
        "silence_duration",
    ):
        if key in voice:
            out[key] = voice[key]

    if "enabled" in stt:
        out["stt_enabled"] = bool(stt["enabled"])
    if stt.get("provider"):
        out["stt_provider"] = str(stt["provider"])
    local = stt.get("local")
    if isinstance(local, dict) and local.get("model"):
        out["stt_model"] = str(local["model"])

    if tts.get("provider"):
        out["tts_provider"] = str(tts["provider"])
    edge = tts.get("edge")
    if isinstance(edge, dict) and edge.get("voice"):
        out["tts_voice"] = str(edge["voice"])

    # Alpha OS local config overrides when Hermes home is missing
    if not hermes_config_path().exists():
        out["wake_word"] = str(get("voice.wake_word", out["wake_word"]))
        out["server_wake"] = bool(get("voice.enabled", out["server_wake"]))
        out["browser_wake"] = bool(get("voice.browser_wake", out["browser_wake"]))
        out["grok_oauth"] = bool(get("voice.providers.grok_oauth", out["grok_oauth"]))

    out["hermes_config_path"] = str(hermes_config_path())
    out["hermes_config_exists"] = hermes_config_path().exists()
    return out


def apply_voice_config(updates: dict[str, Any]) -> dict[str, Any]:
    """Persist voice settings to ~/.hermes/config.yaml and mirror to ~/.alpha-os."""
    cfg = read_hermes_config()
    alpha = dict(_alpha_os_block(cfg))
    voice = dict(_voice_block(cfg))
    stt = dict(_stt_block(cfg))
    tts = dict(_tts_block(cfg))

    if updates.get("wake_word") is not None:
        wake = str(updates["wake_word"]).strip() or DEFAULT_WAKE
        alpha["wake_word"] = wake
        set_key("voice.wake_word", wake)

    if updates.get("browser_wake") is not None:
        alpha["browser_wake"] = bool(updates["browser_wake"])
        set_key("voice.browser_wake", bool(updates["browser_wake"]))

    if updates.get("server_wake") is not None:
        alpha["server_wake"] = bool(updates["server_wake"])
        set_key("voice.enabled", bool(updates["server_wake"]))

    if updates.get("grok_oauth") is not None:
        alpha["grok_oauth"] = bool(updates["grok_oauth"])
        set_key("voice.providers.grok_oauth", bool(updates["grok_oauth"]))

    if updates.get("provider_id") and updates.get("provider_enabled") is not None:
        set_key(
            f"voice.providers.{updates['provider_id']}",
            bool(updates["provider_enabled"]),
        )

    for key in (
        "record_key",
        "max_recording_seconds",
        "auto_tts",
        "beep_enabled",
        "silence_threshold",
        "silence_duration",
    ):
        if updates.get(key) is not None:
            voice[key] = updates[key]

    if updates.get("stt_enabled") is not None:
        stt["enabled"] = bool(updates["stt_enabled"])
    if updates.get("stt_provider") is not None:
        stt["provider"] = str(updates["stt_provider"])
    if updates.get("stt_model") is not None:
        local = stt.setdefault("local", {})
        if isinstance(local, dict):
            local["model"] = str(updates["stt_model"])

    if updates.get("tts_provider") is not None:
        tts["provider"] = str(updates["tts_provider"])
    if updates.get("tts_voice") is not None:
        edge = tts.setdefault("edge", {})
        if isinstance(edge, dict):
            edge["voice"] = str(updates["tts_voice"])

    cfg["alpha_os"] = alpha
    if voice:
        cfg["voice"] = voice
    if stt:
        cfg["stt"] = stt
    if tts:
        cfg["tts"] = tts

    write_hermes_config(cfg)

    if updates.get("wake_word") is not None:
        try:
            from alpha_os.voice.openclaw_voicewake import write_voicewake, wake_word_to_triggers

            write_voicewake(wake_word_to_triggers(str(updates["wake_word"]).strip() or DEFAULT_WAKE))
        except Exception:
            pass

    return load_voice_config()