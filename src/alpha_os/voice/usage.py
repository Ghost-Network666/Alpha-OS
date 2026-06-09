"""In-memory voice session usage (TTS/STT characters and token estimates)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


def _est_tokens(characters: int) -> int:
    """Rough token estimate for billing display (chars / 4)."""
    return max(0, characters // 4)


@dataclass
class VoiceUsageSession:
    tts_requests: int = 0
    tts_characters: int = 0
    stt_requests: int = 0
    stt_characters: int = 0
    last_tts_provider: str = ""
    last_stt_provider: str = ""
    last_tts_chars: int = 0
    last_stt_chars: int = 0
    last_tts_at: float | None = None
    last_stt_at: float | None = None
    _started_at: float = field(default_factory=time.time)

    def record_tts(self, *, provider: str, characters: int) -> None:
        chars = max(0, characters)
        self.tts_requests += 1
        self.tts_characters += chars
        self.last_tts_provider = provider
        self.last_tts_chars = chars
        self.last_tts_at = time.time()

    def record_stt(self, *, provider: str, characters: int) -> None:
        chars = max(0, characters)
        self.stt_requests += 1
        self.stt_characters += chars
        self.last_stt_provider = provider
        self.last_stt_chars = chars
        self.last_stt_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        total_chars = self.tts_characters + self.stt_characters
        return {
            "tts_requests": self.tts_requests,
            "tts_characters": self.tts_characters,
            "stt_requests": self.stt_requests,
            "stt_characters": self.stt_characters,
            "estimated_tokens": _est_tokens(total_chars),
            "tts_estimated_tokens": _est_tokens(self.tts_characters),
            "stt_estimated_tokens": _est_tokens(self.stt_characters),
            "last_tts_provider": self.last_tts_provider,
            "last_stt_provider": self.last_stt_provider,
            "last_tts_chars": self.last_tts_chars,
            "last_stt_chars": self.last_stt_chars,
            "last_tts_at": self.last_tts_at,
            "last_stt_at": self.last_stt_at,
            "session_started_at": self._started_at,
        }


_SESSION = VoiceUsageSession()


def voice_usage_session() -> VoiceUsageSession:
    return _SESSION


def reset_voice_usage() -> dict[str, Any]:
    global _SESSION
    _SESSION = VoiceUsageSession()
    return _SESSION.to_dict()