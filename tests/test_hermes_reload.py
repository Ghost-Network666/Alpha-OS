import pytest

from alpha_os.voice.hermes_reload import reload_hermes_gateway


@pytest.mark.asyncio
async def test_reload_hermes_gateway_http_success(monkeypatch):
    class FakeResponse:
        status_code = 200
        content = b'{"ok": true}'

        def json(self):
            return {"ok": True}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None):
            if url.endswith("/v1/reload"):
                return FakeResponse()
            raise RuntimeError("not found")

        async def get(self, url, headers=None):
            raise RuntimeError("not found")

    monkeypatch.setattr("alpha_os.voice.hermes_reload.httpx.AsyncClient", FakeClient)
    monkeypatch.setattr("alpha_os.voice.hermes_reload._hermes_api_key", lambda: "test-key")

    result = await reload_hermes_gateway("http://127.0.0.1:8642", hermes_connected=True)
    assert result["ok"] is True
    assert result["method"] == "http"
    assert result["path"] == "/v1/reload"