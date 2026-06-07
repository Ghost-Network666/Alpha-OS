"""Optional voice input — graceful when dependencies unavailable."""

from .hermes_sync import apply_voice_config, load_voice_config
from .loop import VoiceLoop, voice_available
from .providers import get_voice_providers
from .tts_stream import synthesize_tts
from .wakeword import DEFAULT_WAKE_WORD

__all__ = [
    "VoiceLoop",
    "voice_available",
    "get_voice_providers",
    "apply_voice_config",
    "load_voice_config",
    "synthesize_tts",
    "DEFAULT_WAKE_WORD",
]