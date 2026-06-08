"""Tests for optional API token auth."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alpha_os.auth import auth_enabled, requires_auth, token_valid
from alpha_os.server import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_auth_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALPHA_OS_API_TOKEN", raising=False)
    assert auth_enabled() is False
    assert token_valid(None) is True
    assert requires_auth("/api/state") is False


def test_auth_requires_token_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALPHA_OS_API_TOKEN", "secret-token")
    assert auth_enabled() is True
    assert token_valid("secret-token") is True
    assert token_valid("wrong") is False
    assert requires_auth("/api/state") is True
    assert requires_auth("/health") is False


def test_health_public_even_with_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALPHA_OS_API_TOKEN", "secret-token")
    res = client.get("/health")
    assert res.status_code == 200


def test_api_state_requires_token_when_set(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALPHA_OS_API_TOKEN", "secret-token")
    denied = client.get("/api/state")
    assert denied.status_code == 401

    ok = client.get(
        "/api/state",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert ok.status_code == 200


def test_bootstrap_public_with_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALPHA_OS_API_TOKEN", "secret-token")
    res = client.get("/api/bootstrap")
    assert res.status_code == 200
    data = res.json()
    assert data["auth_required"] is True
    assert "token=secret-token" in data["ws_url"]


def test_mutating_route_requires_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALPHA_OS_API_TOKEN", "secret-token")
    denied = client.post("/api/mcp/refresh")
    assert denied.status_code == 401

    ok = client.post(
        "/api/mcp/refresh",
        headers={"X-Alpha-OS-Token": "secret-token"},
    )
    assert ok.status_code == 200