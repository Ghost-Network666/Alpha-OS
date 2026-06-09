from alpha_os.voice.hermes_sync import _resolve_tts


def test_resolve_tts_respects_explicit_elevenlabs():
    tts = {
        "provider": "elevenlabs",
        "elevenlabs": {"voice_id": "abc123", "model_id": "eleven_multilingual_v2"},
        "xai": {"voice_id": "eve"},
    }
    model = {"provider": "xai-oauth", "default": "grok-4.3"}
    provider, voice = _resolve_tts(tts, model)
    assert provider == "elevenlabs"
    assert voice == "abc123"


def test_resolve_tts_defaults_xai_when_unset_and_grok():
    tts = {"xai": {"voice_id": "eve"}}
    model = {"provider": "xai-oauth", "default": "grok-4.3"}
    provider, voice = _resolve_tts(tts, model)
    assert provider == "xai"
    assert voice == "eve"