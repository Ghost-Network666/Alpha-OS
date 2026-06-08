"""Optional voice input — graceful when dependencies unavailable."""

from .hermes_sync import (
    apply_voice_config,
    ensure_hermes_alpha_os_block,
    load_voice_config,
    sync_voice_to_alpha_os,
)
from .loop import VoiceLoop, voice_available
from .providers import get_voice_providers
from .wakeword import DEFAULT_WAKE_WORD

__all__ = [
    "VoiceLoop",
    "voice_available",
    "get_voice_providers",
    "apply_voice_config",
    "ensure_hermes_alpha_os_block",
    "load_voice_config",
    "sync_voice_to_alpha_os",
    "DEFAULT_WAKE_WORD",
]