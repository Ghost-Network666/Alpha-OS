import pytest

from alpha_os.voice import elevenlabs as el


@pytest.mark.asyncio
async def test_list_elevenlabs_voices_without_key():
    result = await el.list_elevenlabs_voices()
    assert result["available"] is False
    assert result["voices"] == []


@pytest.mark.asyncio
async def test_list_elevenlabs_voices_mock(monkeypatch):
    monkeypatch.setattr(el, "elevenlabs_api_key", lambda: "test-key")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "voices": [
                    {"voice_id": "abc123", "name": "Rachel", "category": "premade"},
                    {"voice_id": "xyz", "name": "Adam", "category": "premade"},
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers=None, params=None):
            return FakeResponse()

    monkeypatch.setattr(el.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    result = await el.list_elevenlabs_voices()
    assert result["available"] is True
    assert len(result["voices"]) == 2
    ids = {v["voice_id"] for v in result["voices"]}
    assert ids == {"abc123", "xyz"}
    rachel = next(v for v in result["voices"] if v["voice_id"] == "abc123")
    assert "Rachel" in rachel["label"]


@pytest.mark.asyncio
async def test_synthesize_elevenlabs_mock(monkeypatch):
    monkeypatch.setattr(el, "elevenlabs_api_key", lambda: "test-key")
    monkeypatch.setattr(el, "_elevenlabs_block", lambda: {"voice_id": "v1", "model_id": "m1"})

    class FakeResponse:
        status_code = 200
        content = b"mp3bytes"
        text = ""

        @property
        def headers(self):
            return {"content-type": "audio/mpeg"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers=None, json=None):
            assert "v1" in url
            assert json["model_id"] == "m1"
            return FakeResponse()

    monkeypatch.setattr(el.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    result = await el.synthesize_elevenlabs("hello")
    assert result is not None
    audio, ctype = result
    assert audio == b"mp3bytes"
    assert ctype == "audio/mpeg"


@pytest.mark.asyncio
async def test_synthesize_tts_elevenlabs_branch(monkeypatch):
    from alpha_os.voice.tts_stream import synthesize_tts

    async def fake_el(text, *, voice_id=None, model_id=None):
        return b"el-audio", "audio/mpeg"

    monkeypatch.setattr(
        "alpha_os.voice.elevenlabs.synthesize_elevenlabs",
        fake_el,
    )

    result = await synthesize_tts("hello", provider="elevenlabs", voice="voice-1")
    assert result is not None
    assert result.provider == "elevenlabs"
    assert result.audio == b"el-audio"