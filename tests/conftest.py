"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_api_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Most unit tests assume auth is disabled."""
    monkeypatch.delenv("ALPHA_OS_API_TOKEN", raising=False)


@pytest.fixture(autouse=True)
def _offline_server_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent tests from picking up a live Hermes/OpenClaw on the dev machine."""
    import alpha_os.server as srv

    async def _offline_init() -> None:
        srv._active_runtime = "offline"
        srv.HERMES_BRIDGE._connected = False
        srv.OPENCLAW_BRIDGE._connected = False

    monkeypatch.setattr(srv, "_init_bridges", _offline_init)
    srv._active_runtime = "offline"
    srv.HERMES_BRIDGE._connected = False
    srv.OPENCLAW_BRIDGE._connected = False