"""Unit tests for runtime detector."""

from __future__ import annotations

from pathlib import Path

import pytest

from alpha_os.bridges.detector import (
    RuntimeInfo,
    color_for_index,
    detect_best,
    detect_hermes,
    detect_openclaw,
    hermes_installed,
    openclaw_installed,
)


def test_runtime_install_flags_are_boolean() -> None:
    assert isinstance(hermes_installed(), bool)
    assert isinstance(openclaw_installed(), bool)


def test_color_for_index_wraps_palette() -> None:
    c0 = color_for_index(0)
    c5 = color_for_index(5)
    assert c0.startswith("#")
    assert c5.startswith("#")


@pytest.mark.asyncio
async def test_detect_hermes_no_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "missing-hermes"
    monkeypatch.setattr(
        "alpha_os.bridges.detector.hermes_home",
        lambda: missing,
    )
    info = await detect_hermes()
    assert info.name == "hermes"
    assert info.connected is False
    assert "no ~/.hermes" in info.details.get("reason", "")


@pytest.mark.asyncio
async def test_detect_hermes_connected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hermes = tmp_path / ".hermes"
    hermes.mkdir()
    monkeypatch.setattr("alpha_os.bridges.detector.hermes_home", lambda: hermes)
    monkeypatch.setattr(
        "alpha_os.bridges.detector.read_hermes_env",
        lambda: {"API_SERVER_KEY": "k"},
    )
    monkeypatch.setattr(
        "alpha_os.bridges.detector._hermes_candidates",
        lambda: ["http://127.0.0.1:8642"],
    )

    async def _probe_ok(url: str, headers=None, timeout: float = 3.0) -> bool:
        return "8642" in url

    monkeypatch.setattr("alpha_os.bridges.detector._probe_http", _probe_ok)

    info = await detect_hermes()
    assert info.connected is True
    assert info.gateway_url == "http://127.0.0.1:8642"


@pytest.mark.asyncio
async def test_detect_openclaw_reads_token_from_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openclaw = tmp_path / ".openclaw"
    openclaw.mkdir()
    monkeypatch.setattr("alpha_os.bridges.detector.openclaw_home", lambda: openclaw)
    monkeypatch.setattr(
        "alpha_os.bridges.detector.read_openclaw_env",
        lambda: {"OPENCLAW_GATEWAY_TOKEN": "oc-secret"},
    )
    monkeypatch.setattr(
        "alpha_os.bridges.detector._openclaw_candidates",
        lambda: ["http://127.0.0.1:18789"],
    )
    async def _probe_no(*_a, **_k) -> bool:
        return False

    monkeypatch.setattr("alpha_os.bridges.detector._probe_http", _probe_no)
    monkeypatch.setattr(
        "alpha_os.bridges.detector.read_openclaw_config",
        lambda: {"gateway": {"port": 18789}},
    )

    info = await detect_openclaw()
    assert info.api_key == "oc-secret"
    assert info.ws_url == "ws://127.0.0.1:18789"


@pytest.mark.asyncio
async def test_detect_best_prefers_connected_hermes(monkeypatch: pytest.MonkeyPatch) -> None:
    hermes = RuntimeInfo(name="hermes", connected=True, gateway_url="http://127.0.0.1:8642")
    openclaw = RuntimeInfo(name="openclaw", connected=False)

    async def _hermes() -> RuntimeInfo:
        return hermes

    async def _openclaw() -> RuntimeInfo:
        return openclaw

    monkeypatch.setattr("alpha_os.bridges.detector.detect_hermes", _hermes)
    monkeypatch.setattr("alpha_os.bridges.detector.detect_openclaw", _openclaw)

    best = await detect_best()
    assert best.name == "hermes"
    assert best.connected is True