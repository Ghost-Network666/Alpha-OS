"""Server-side TTS: Edge, Hermes gateway, and Grok/xAI audio streams."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from alpha_os.config import read_hermes_config, read_hermes_env
from alpha_os.voice.hermes_sync import load_voice_config

logger = logging.getLogger("alpha_os.voice")

MAX_TTS_CHARS = 5000

HERMES_TTS_PATHS: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "/v1/audio/speech",
        {
            "model": "tts-1",
            "input": "{text}",
            "voice": "{voice}",
            "response_format": "mp3",
        },
    ),
    ("/api/tts", {"text": "{text}", "voice": "{voice}"}),
    ("/v1/tts", {"text": "{text}", "voice": "{voice}", "format": "mp3"}),
)


@dataclass
class TtsResult:
    audio: bytes
    content_type: str
    provider: str


def _truncate(text: str, limit: int = MAX_TTS_CHARS) -> str:
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 3] + "..."


def _hermes_headers() -> dict[str, str]:
    env = read_hermes_env()
    key = env.get("API_SERVER_KEY") or env.get("HERMES_API_KEY") or ""
    headers = {"Accept": "audio/mpeg,application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _resolve_voice(provider: str, voice: Optional[str]) -> str:
    cfg = load_voice_config()
    if voice:
        return voice
    if provider in {"edge", "grok", "xai"}:
        return str(cfg.get("tts_voice") or "en-US-AriaNeural")
    hermes = read_hermes_config()
    tts = hermes.get("tts") if isinstance(hermes.get("tts"), dict) else {}
    edge = tts.get("edge") if isinstance(tts.get("edge"), dict) else {}
    if edge.get("voice"):
        return str(edge["voice"])
    xai = tts.get("xai") if isinstance(tts.get("xai"), dict) else {}
    if xai.get("voice_id"):
        return str(xai["voice_id"])
    return "en-US-AriaNeural"


async def _synthesize_edge(text: str, voice: str) -> Optional[TtsResult]:
    try:
        import edge_tts
    except ImportError:
        return None

    communicate = edge_tts.Communicate(_truncate(text), voice=voice)
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            data = chunk.get("data")
            if isinstance(data, (bytes, bytearray)):
                chunks.append(bytes(data))
    if not chunks:
        return None
    return TtsResult(audio=b"".join(chunks), content_type="audio/mpeg", provider="edge")


async def _synthesize_hermes_gateway(
    text: str,
    *,
    gateway_url: str,
    provider: str,
    voice: str,
) -> Optional[TtsResult]:
    base = gateway_url.rstrip("/")
    headers = _hermes_headers()
    body_text = _truncate(text)

    async with httpx.AsyncClient(timeout=60.0) as client:
        for path, template in HERMES_TTS_PATHS:
            payload: dict[str, Any] = {}
            for key, val in template.items():
                if isinstance(val, str):
                    payload[key] = val.replace("{text}", body_text).replace("{voice}", voice)
                else:
                    payload[key] = val
            if provider in {"grok", "xai"}:
                payload["provider"] = "xai"
            try:
                r = await client.post(
                    f"{base}{path}",
                    headers=headers,
                    json=payload,
                )
                if r.status_code != 200 or not r.content:
                    continue
                ctype = r.headers.get("content-type", "audio/mpeg").split(";")[0].strip()
                if ctype.startswith("application/json"):
                    data = r.json()
                    audio_b64 = (
                        data.get("audio")
                        or data.get("data")
                        or (data.get("result") or {}).get("audio")
                    )
                    if isinstance(audio_b64, str):
                        import base64

                        raw = base64.b64decode(audio_b64)
                        return TtsResult(audio=raw, content_type="audio/mpeg", provider=provider)
                    continue
                return TtsResult(
                    audio=r.content,
                    content_type=ctype or "audio/mpeg",
                    provider=provider,
                )
            except Exception:
                continue
    return None


async def _synthesize_xai_direct(text: str, voice: str) -> Optional[TtsResult]:
    env = read_hermes_env()
    api_key = env.get("XAI_API_KEY") or env.get("XAI_KEY") or ""
    if not api_key:
        return None

    base = env.get("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
    payload = {
        "model": "grok-tts",
        "input": _truncate(text, 15000),
        "voice": voice or "eve",
        "response_format": "mp3",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{base}/audio/speech",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json=payload,
            )
            if r.status_code == 200 and r.content:
                ctype = r.headers.get("content-type", "audio/mpeg").split(";")[0].strip()
                return TtsResult(audio=r.content, content_type=ctype, provider="grok")
    except Exception as exc:
        logger.debug("xAI direct TTS failed: %s", exc)
    return None


async def synthesize_tts(
    text: str,
    *,
    provider: Optional[str] = None,
    voice: Optional[str] = None,
    hermes_gateway_url: Optional[str] = None,
    hermes_connected: bool = False,
) -> Optional[TtsResult]:
    """Synthesize speech bytes for Alpha replies."""
    trimmed = _truncate(text)
    if not trimmed:
        return None

    cfg = load_voice_config()
    prov = (provider or cfg.get("tts_provider") or "edge").strip().lower()
    resolved_voice = _resolve_voice(prov, voice)

    if prov in {"grok", "xai"}:
        if hermes_gateway_url:
            gw = await _synthesize_hermes_gateway(
                trimmed,
                gateway_url=hermes_gateway_url,
                provider="grok",
                voice=resolved_voice,
            )
            if gw:
                return gw
        direct = await _synthesize_xai_direct(trimmed, resolved_voice)
        if direct:
            return direct
        prov = "edge"

    if prov == "edge" or prov in {"neutts", "piper", "kittentts"}:
        edge = await _synthesize_edge(trimmed, resolved_voice)
        if edge:
            return edge
        if hermes_connected and hermes_gateway_url:
            gw = await _synthesize_hermes_gateway(
                trimmed,
                gateway_url=hermes_gateway_url,
                provider="edge",
                voice=resolved_voice,
            )
            if gw:
                return gw

    if hermes_connected and hermes_gateway_url:
        gw = await _synthesize_hermes_gateway(
            trimmed,
            gateway_url=hermes_gateway_url,
            provider=prov,
            voice=resolved_voice,
        )
        if gw:
            return gw

    return await _synthesize_edge(trimmed, resolved_voice)