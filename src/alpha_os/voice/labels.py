"""Human-readable voice provider labels and local/cloud classification."""

from __future__ import annotations

LOCAL_TTS = frozenset({"edge", "neutts", "piper", "kittentts", "local"})
LOCAL_STT = frozenset({"local"})

TTS_LABELS: dict[str, str] = {
    "xai": "xAI / Grok",
    "grok": "xAI / Grok",
    "elevenlabs": "ElevenLabs",
    "edge": "Edge TTS (free)",
    "openai": "OpenAI TTS",
    "mistral": "Mistral TTS",
    "neutts": "NeuTTS (local)",
    "piper": "Piper (local)",
    "kittentts": "KittenTTS (local)",
    "local": "Local TTS",
}

STT_LABELS: dict[str, str] = {
    "local": "Whisper (local)",
    "xai": "xAI / Grok STT",
    "groq": "Groq Whisper",
    "openai": "OpenAI Whisper",
    "mistral": "Mistral Voxtral",
    "elevenlabs": "ElevenLabs Scribe",
}


def tts_provider_label(provider: str) -> str:
    key = (provider or "edge").strip().lower()
    return TTS_LABELS.get(key, key or "edge")


def stt_provider_label(provider: str) -> str:
    key = (provider or "local").strip().lower()
    return STT_LABELS.get(key, key or "local")


def is_local_tts(provider: str) -> bool:
    return (provider or "").strip().lower() in LOCAL_TTS


def is_local_stt(provider: str) -> bool:
    return (provider or "").strip().lower() in LOCAL_STT