"""Unit tests for FastAPI routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alpha_os.server import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_version(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["service"] == "alpha-os"
    assert "version" in data


def test_ready_returns_runtime_fields(client: TestClient) -> None:
    res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "runtime" in data
    assert "mcp_servers" in data


def test_bootstrap_includes_env_sources(client: TestClient) -> None:
    res = client.get("/api/bootstrap")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "ws_url" in data
    assert "env_sources" in data
    assert data["auth_required"] is False


def test_api_state_offline_has_mcp_panel(client: TestClient) -> None:
    res = client.get("/api/state")
    assert res.status_code == 200
    data = res.json()
    assert "mcp" in data
    assert "servers" in data["mcp"]
    assert data.get("gateway_online") is False
    assert data.get("runtime") == "offline"


def test_api_command_empty_reply(client: TestClient) -> None:
    res = client.post("/api/command", json={"command": ""})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert "service" in body["reply"].lower()


def test_api_command_offline_fallback(client: TestClient) -> None:
    res = client.post("/api/command", json={"command": "hello alpha"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["relayed"] is False
    assert body["reply"]


def test_api_mcp_get(client: TestClient) -> None:
    res = client.get("/api/mcp")
    assert res.status_code == 200
    data = res.json()
    assert "servers" in data
    assert "server_count" in data


def test_api_config_roundtrip(client: TestClient, tmp_path, monkeypatch) -> None:
    alpha_home = tmp_path / "alpha-os"
    alpha_home.mkdir()
    monkeypatch.setattr("alpha_os.config.CONFIG_DIR", alpha_home)
    monkeypatch.setattr("alpha_os.config.CONFIG_PATH", alpha_home / "config.yaml")

    post = client.post(
        "/api/config",
        json={"runtime": "openclaw", "openclaw_ws_url": "ws://127.0.0.1:19999"},
    )
    assert post.status_code == 200
    assert post.json()["ok"] is True

    get_res = client.get("/api/config")
    assert get_res.status_code == 200
    cfg = get_res.json()
    assert cfg.get("runtime") == "openclaw"


def test_voice_elevenlabs_voices_without_key(client: TestClient) -> None:
    res = client.get("/api/voice/elevenlabs/voices")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is False
    assert data["voices"] == []


def test_voice_tts_empty_text(client: TestClient) -> None:
    res = client.post("/api/voice/tts", json={"text": "   "})
    assert res.status_code == 502


def test_voice_tts_edge_mock(client: TestClient, monkeypatch) -> None:
    from alpha_os.voice.tts_stream import TtsResult

    async def fake_synthesize(*args, **kwargs):
        return TtsResult(audio=b"abc", content_type="audio/mpeg", provider="edge")

    monkeypatch.setattr("alpha_os.voice.tts_stream.synthesize_tts", fake_synthesize)

    res = client.post(
        "/api/voice/tts",
        json={"text": "hello", "provider": "edge", "voice": "en-US-AriaNeural"},
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("audio/")
    assert res.content == b"abc"