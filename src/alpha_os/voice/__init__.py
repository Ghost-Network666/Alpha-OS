"""Optional voice input — graceful when dependencies unavailable."""

from .loop import VoiceLoop, voice_available

__all__ = ["VoiceLoop", "voice_available"]