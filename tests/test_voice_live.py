from alpha_os.voice.live import build_voice_live
from alpha_os.voice.usage import reset_voice_usage, voice_usage_session


def test_build_voice_live_includes_providers(monkeypatch):
    monkeypatch.setattr(
        "alpha_os.voice.live.load_voice_config",
        lambda profile=None: {
            "tts_provider": "xai",
            "tts_voice": "eve",
            "stt_provider": "xai",
            "stt_model": "base",
            "auto_tts": True,
            "stt_enabled": True,
            "browser_wake": True,
            "wake_word": "hey alpha",
        },
    )
    reset_voice_usage()
    live = build_voice_live()
    assert live["tts_provider"] == "xai"
    assert live["tts_provider_label"] == "xAI / Grok"
    assert live["tts_voice"] == "eve"
    assert live["tts_local"] is False
    assert "session" in live


def test_voice_usage_records_tts():
    reset_voice_usage()
    session = voice_usage_session()
    session.record_tts(provider="elevenlabs", characters=120)
    data = session.to_dict()
    assert data["tts_requests"] == 1
    assert data["tts_characters"] == 120
    assert data["estimated_tokens"] == 30