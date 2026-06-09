"""ElevenLabs TTS and voice library — https://elevenlabs.io/docs/product-guides/voices/voice-library"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from alpha_os.config import read_hermes_config, read_hermes_env

logger = logging.getLogger("alpha_os.voice")

ELEVENLABS_API_BASE = "https://api.elevenlabs.io"
DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Rachel (premade)
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"


def elevenlabs_api_key() -> str:
    env = read_hermes_env()
    return (env.get("ELEVENLABS_API_KEY") or "").strip()


def _elevenlabs_block() -> dict[str, Any]:
    hermes = read_hermes_config()
    tts = hermes.get("tts") if isinstance(hermes.get("tts"), dict) else {}
    block = tts.get("elevenlabs")
    return block if isinstance(block, dict) else {}


def elevenlabs_model_id() -> str:
    block = _elevenlabs_block()
    return str(block.get("model_id") or block.get("model") or DEFAULT_MODEL_ID)


def elevenlabs_configured() -> bool:
    return bool(elevenlabs_api_key())


def _voice_label(voice: dict[str, Any]) -> str:
    name = str(voice.get("name") or voice.get("voice_id") or "Voice").strip()
    category = str(voice.get("category") or "").strip()
    return f"{name} ({category})" if category else name


async def list_elevenlabs_voices(
    *,
    search: str | None = None,
    page_size: int = 100,
) -> dict[str, Any]:
    """List voices from the ElevenLabs voice library (account + premade)."""
    api_key = elevenlabs_api_key()
    if not api_key:
        return {"available": False, "voices": [], "error": "ELEVENLABS_API_KEY not set"}

    params: dict[str, Any] = {
        "page_size": min(max(page_size, 1), 100),
        "include_total_count": False,
    }
    if search:
        params["search"] = search.strip()

    headers = {"Accept": "application/json", "xi-api-key": api_key}

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Prefer v2 search API; fall back to legacy v1 list.
        for url in (f"{ELEVENLABS_API_BASE}/v2/voices", f"{ELEVENLABS_API_BASE}/v1/voices"):
            try:
                r = await client.get(url, headers=headers, params=params if "v2" in url else None)
                if r.status_code != 200:
                    continue
                payload = r.json()
                raw = payload.get("voices") if isinstance(payload, dict) else None
                if not isinstance(raw, list):
                    continue

                voices: list[dict[str, str]] = []
                for voice in raw:
                    if not isinstance(voice, dict):
                        continue
                    voice_id = str(voice.get("voice_id") or "").strip()
                    if not voice_id:
                        continue
                    voices.append(
                        {
                            "voice_id": voice_id,
                            "name": str(voice.get("name") or voice_id),
                            "label": _voice_label(voice),
                            "category": str(voice.get("category") or ""),
                        }
                    )

                voices.sort(key=lambda item: str(item.get("label") or "").lower())
                return {"available": True, "voices": voices}
            except Exception as exc:
                logger.debug("ElevenLabs voice list via %s failed: %s", url, exc)

    return {"available": False, "voices": [], "error": "Could not load ElevenLabs voices"}


async def synthesize_elevenlabs(
    text: str,
    *,
    voice_id: str | None = None,
    model_id: str | None = None,
) -> Optional[tuple[bytes, str]]:
    """Synthesize speech via ElevenLabs text-to-speech API. Returns (audio, content_type)."""
    api_key = elevenlabs_api_key()
    if not api_key:
        return None

    block = _elevenlabs_block()
    resolved_voice = (voice_id or block.get("voice_id") or DEFAULT_VOICE_ID).strip()
    resolved_model = (model_id or block.get("model_id") or block.get("model") or DEFAULT_MODEL_ID).strip()
    if not resolved_voice:
        return None

    url = (
        f"{ELEVENLABS_API_BASE}/v1/text-to-speech/{resolved_voice}"
        f"?output_format={DEFAULT_OUTPUT_FORMAT}"
    )
    payload = {"text": text, "model_id": resolved_model}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                url,
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json=payload,
            )
            if r.status_code == 200 and r.content:
                ctype = r.headers.get("content-type", "audio/mpeg").split(";")[0].strip()
                return r.content, ctype or "audio/mpeg"
            logger.debug("ElevenLabs TTS HTTP %s: %s", r.status_code, r.text[:200])
    except Exception as exc:
        logger.debug("ElevenLabs TTS failed: %s", exc)
    return None