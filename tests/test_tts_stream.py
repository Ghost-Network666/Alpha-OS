import pytest

from alpha_os.voice.tts_stream import _truncate, synthesize_tts


def test_truncate_limits_length():
    assert _truncate("short") == "short"
    long_text = "x" * 6000
    assert len(_truncate(long_text)) == 5000
    assert _truncate(long_text).endswith("...")


@pytest.mark.asyncio
async def test_synthesize_tts_empty_text():
    assert await synthesize_tts("   ") is None


@pytest.mark.asyncio
async def test_synthesize_tts_edge_mock(monkeypatch):
    class FakeCommunicate:
        def __init__(self, text, voice=None):
            self.text = text
            self.voice = voice

        async def stream(self):
            yield {"type": "audio", "data": b"abc"}

    fake_module = type("edge_tts", (), {"Communicate": FakeCommunicate})
    monkeypatch.setitem(__import__("sys").modules, "edge_tts", fake_module)

    result = await synthesize_tts("hello", provider="edge", voice="en-US-AriaNeural")
    assert result is not None
    assert result.audio == b"abc"
    assert result.provider == "edge"