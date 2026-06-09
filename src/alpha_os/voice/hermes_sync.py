"""Sync Alpha OS voice settings with active Hermes profile config."""

from __future__ import annotations

from typing import Any

from alpha_os.config import (
    active_hermes_profile,
    get,
    hermes_config_path,
    load_config,
    read_hermes_config,
    read_hermes_profile_config,
    save_config,
    set_active_hermes_profile,
    set_key,
    write_hermes_config,
    _read_yaml,
    HERMES_CONFIG_PATH,
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

_TTS_MODEL_KEYS: dict[str, tuple[str, str]] = {
    "elevenlabs": ("elevenlabs", "model_id"),
    "mistral": ("mistral", "model"),
    "openai": ("openai", "model"),
}

_TTS_VOICE_KEYS: dict[str, tuple[str, str]] = {
    "edge": ("edge", "voice"),
    "xai": ("xai", "voice_id"),
    "openai": ("openai", "voice"),
    "elevenlabs": ("elevenlabs", "voice_id"),
    "mistral": ("mistral", "voice_id"),
    "piper": ("piper", "voice"),
    "neutts": ("neutts", "voice"),
}

_STT_MODEL_KEYS: dict[str, tuple[str, str]] = {
    "local": ("local", "model"),
    "openai": ("openai", "model"),
    "mistral": ("mistral", "model"),
    "elevenlabs": ("elevenlabs", "model_id"),
    "groq": ("groq", "model"),
    "xai": ("xai", "model"),
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


def _model_block(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("model")
    return block if isinstance(block, dict) else {}


def _uses_grok_oauth(model: dict[str, Any]) -> bool:
    provider = str(model.get("provider") or "").lower()
    default_model = str(model.get("default") or "").lower()
    return (
        "xai" in provider
        or "grok" in provider
        or default_model.startswith("grok")
    )


def _tts_model_for_provider(tts: dict[str, Any], provider: str) -> str | None:
    block_key, model_key = _TTS_MODEL_KEYS.get(provider, ("", ""))
    if not block_key:
        return None
    block = tts.get(block_key)
    if isinstance(block, dict):
        val = block.get(model_key) or block.get("model")
        if val:
            return str(val)
    return None


def _tts_voice_for_provider(tts: dict[str, Any], provider: str) -> str | None:
    block_key, voice_key = _TTS_VOICE_KEYS.get(provider, ("edge", "voice"))
    block = tts.get(block_key)
    if isinstance(block, dict) and block.get(voice_key):
        return str(block[voice_key])
    return None


def _stt_model_for_provider(stt: dict[str, Any], provider: str) -> str | None:
    block_key, model_key = _STT_MODEL_KEYS.get(provider, ("local", "model"))
    block = stt.get(block_key)
    if isinstance(block, dict) and block.get(model_key):
        return str(block[model_key])
    return None


def _resolve_tts(tts: dict[str, Any], model: dict[str, Any]) -> tuple[str, str]:
    """Pick TTS provider + voice from Hermes config; respect explicit tts.provider."""
    explicit = str(tts.get("provider") or "").lower().strip()
    provider = explicit or "edge"
    grok_model = _uses_grok_oauth(model)

    if explicit:
        voice = _tts_voice_for_provider(tts, explicit)
        if voice:
            return explicit, voice

    if grok_model and (not explicit or explicit == "xai"):
        xai_voice = _tts_voice_for_provider(tts, "xai")
        if xai_voice:
            return "xai", xai_voice

    voice = _tts_voice_for_provider(tts, provider)
    if voice:
        return provider, voice

    for fallback in ("xai", "edge", "openai", "elevenlabs"):
        voice = _tts_voice_for_provider(tts, fallback)
        if voice:
            return fallback, voice

    return str(VOICE_DEFAULTS["tts_provider"]), str(VOICE_DEFAULTS["tts_voice"])


def _merged_hermes_config(profile: str | None = None) -> dict[str, Any]:
    """Profile config, with global alpha_os block merged when missing."""
    name = (profile or active_hermes_profile()).strip() or "default"
    cfg = read_hermes_profile_config(name) if name else read_hermes_config()
    if not cfg:
        cfg = read_hermes_config()
    global_cfg = _read_yaml(HERMES_CONFIG_PATH)
    if global_cfg and not _alpha_os_block(cfg) and _alpha_os_block(global_cfg):
        merged = dict(cfg)
        merged["alpha_os"] = dict(_alpha_os_block(global_cfg))
        return merged
    return cfg


def load_voice_config(profile: str | None = None) -> dict[str, Any]:
    """Effective voice config detected from a Hermes profile (active by default)."""
    out = dict(VOICE_DEFAULTS)
    profile_name = (profile or active_hermes_profile()).strip() or "default"
    hermes = _merged_hermes_config(profile_name)
    alpha = _alpha_os_block(hermes)
    voice = _voice_block(hermes)
    stt = _stt_block(hermes)
    tts = _tts_block(hermes)
    model = _model_block(hermes)

    if alpha.get("wake_word"):
        out["wake_word"] = str(alpha["wake_word"]).strip()
    if "browser_wake" in alpha:
        out["browser_wake"] = bool(alpha["browser_wake"])
    if "server_wake" in alpha:
        out["server_wake"] = bool(alpha["server_wake"])
    if "grok_oauth" in alpha:
        out["grok_oauth"] = bool(alpha["grok_oauth"])
    elif _uses_grok_oauth(model):
        out["grok_oauth"] = True

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
    stt_provider = str(stt.get("provider") or out["stt_provider"]).lower()
    out["stt_provider"] = stt_provider
    stt_model = _stt_model_for_provider(stt, stt_provider)
    if stt_model:
        out["stt_model"] = stt_model

    tts_provider, tts_voice = _resolve_tts(tts, model)
    out["tts_provider"] = tts_provider
    out["tts_voice"] = tts_voice
    tts_model = _tts_model_for_provider(tts, tts_provider)
    if tts_model:
        out["tts_model"] = tts_model

    if model.get("default"):
        out["model_default"] = str(model["default"])
    if model.get("provider"):
        out["model_provider"] = str(model["provider"])

    path = hermes_config_path(profile_name)
    if not path.exists():
        out["wake_word"] = str(get("voice.wake_word", out["wake_word"]))
        out["server_wake"] = bool(get("voice.enabled", out["server_wake"]))
        out["browser_wake"] = bool(get("voice.browser_wake", out["browser_wake"]))
        out["grok_oauth"] = bool(get("voice.providers.grok_oauth", out["grok_oauth"]))

    out["hermes_profile"] = profile_name
    out["hermes_config_path"] = str(path)
    out["hermes_config_exists"] = path.exists()
    return out


def sync_voice_to_alpha_os() -> dict[str, Any]:
    """Mirror detected Hermes voice settings into ~/.alpha-os/config.yaml."""
    voice = load_voice_config()
    cfg = load_config()
    cfg.setdefault("voice", {})
    cfg["voice"].update(
        {
            "wake_word": voice["wake_word"],
            "browser_wake": voice["browser_wake"],
            "enabled": voice["server_wake"],
            "server_wake": voice["server_wake"],
            "providers": {"grok_oauth": voice["grok_oauth"]},
            "grok_oauth": voice["grok_oauth"],
            "tts_provider": voice["tts_provider"],
            "tts_voice": voice["tts_voice"],
            "tts_model": voice.get("tts_model"),
            "stt_provider": voice["stt_provider"],
            "stt_model": voice["stt_model"],
            "stt_enabled": voice["stt_enabled"],
            "auto_tts": voice["auto_tts"],
            "beep_enabled": voice["beep_enabled"],
            "record_key": voice["record_key"],
            "max_recording_seconds": voice["max_recording_seconds"],
            "silence_threshold": voice["silence_threshold"],
            "silence_duration": voice["silence_duration"],
            "hermes_profile": voice.get("hermes_profile"),
            "model_provider": voice.get("model_provider"),
            "model_default": voice.get("model_default"),
        }
    )
    save_config(cfg)
    return voice


def ensure_hermes_alpha_os_block() -> None:
    """Ensure alpha_os voice flags exist in active profile Hermes config."""
    cfg = read_hermes_config()
    alpha = dict(_alpha_os_block(cfg))
    model = _model_block(cfg)
    tts, tts_voice = _resolve_tts(_tts_block(cfg), model)
    changed = False

    if "wake_word" not in alpha:
        alpha["wake_word"] = DEFAULT_WAKE
        changed = True
    if "browser_wake" not in alpha:
        alpha["browser_wake"] = True
        changed = True
    if "grok_oauth" not in alpha and _uses_grok_oauth(model):
        alpha["grok_oauth"] = True
        changed = True

    if changed:
        cfg["alpha_os"] = alpha
        write_hermes_config(cfg)

    if _uses_grok_oauth(model) and tts == "xai":
        tts_cfg = dict(_tts_block(cfg))
        if str(tts_cfg.get("provider") or "").lower() != "xai":
            tts_cfg["provider"] = "xai"
            xai = dict(tts_cfg.get("xai") or {})
            if not xai.get("voice_id") and tts_voice:
                xai["voice_id"] = tts_voice
            tts_cfg["xai"] = xai
            cfg["tts"] = tts_cfg
            write_hermes_config(cfg)


def apply_voice_config(updates: dict[str, Any]) -> dict[str, Any]:
    """Persist voice settings to the target Hermes profile and mirror to ~/.alpha-os."""
    profile_name = str(
        updates.get("hermes_profile") or active_hermes_profile()
    ).strip() or "default"
    if updates.get("hermes_profile"):
        set_active_hermes_profile(profile_name)

    cfg = read_hermes_profile_config(profile_name) or read_hermes_config()
    alpha = dict(_alpha_os_block(cfg))
    voice = dict(_voice_block(cfg))
    stt = dict(_stt_block(cfg))
    tts = dict(_tts_block(cfg))
    model = dict(_model_block(cfg))

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
        provider = str(stt.get("provider") or "local")
        block_key, model_key = _STT_MODEL_KEYS.get(provider, ("local", "model"))
        local = stt.setdefault(block_key, {})
        if isinstance(local, dict):
            local[model_key] = str(updates["stt_model"])

    if updates.get("tts_provider") is not None:
        tts["provider"] = str(updates["tts_provider"])
    if updates.get("tts_voice") is not None:
        provider = str(updates.get("tts_provider") or tts.get("provider") or "edge")
        block_key, voice_key = _TTS_VOICE_KEYS.get(provider, ("edge", "voice"))
        block = tts.setdefault(block_key, {})
        if isinstance(block, dict):
            block[voice_key] = str(updates["tts_voice"])

    if updates.get("tts_model") is not None:
        provider = str(updates.get("tts_provider") or tts.get("provider") or "edge")
        block_key, model_key = _TTS_MODEL_KEYS.get(provider, ("", ""))
        if block_key:
            block = tts.setdefault(block_key, {})
            if isinstance(block, dict):
                block[model_key] = str(updates["tts_model"])

    if updates.get("model_provider") is not None:
        model["provider"] = str(updates["model_provider"])
        set_key("voice.model_provider", str(updates["model_provider"]))
    if updates.get("model_default") is not None:
        model["default"] = str(updates["model_default"])
        set_key("voice.model_default", str(updates["model_default"]))

    cfg["alpha_os"] = alpha
    if voice:
        cfg["voice"] = voice
    if stt:
        cfg["stt"] = stt
    if tts:
        cfg["tts"] = tts
    if model:
        cfg["model"] = model

    write_hermes_config(cfg, profile=profile_name)
    return sync_voice_to_alpha_os()


def hermes_config_snapshot() -> dict[str, Any]:
    """Editable Hermes profile blocks for the settings UI."""
    cfg = read_hermes_config()
    return {
        "profile": active_hermes_profile(),
        "config_path": str(hermes_config_path()),
        "alpha_os": _alpha_os_block(cfg),
        "voice": _voice_block(cfg),
        "stt": _stt_block(cfg),
        "tts": _tts_block(cfg),
        "model": _model_block(cfg),
    }