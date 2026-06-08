"""Tests for ~/.hermes/.env and ~/.openclaw/.env injection."""

from __future__ import annotations

from pathlib import Path

import pytest

from alpha_os.config import (
    inject_runtime_env,
    read_hermes_env,
    read_openclaw_env,
    runtime_env_sources,
)


def test_inject_hermes_env_sets_alpha_os_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hermes = tmp_path / ".hermes"
    hermes.mkdir()
    (hermes / ".env").write_text(
        "API_SERVER_KEY=hermes-key\n"
        "ALPHA_OS_PORT=9090\n"
        "ALPHA_OS_API_TOKEN=local-token\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("alpha_os.config.HERMES_HOME", hermes)
    monkeypatch.setattr("alpha_os.config.HERMES_ENV_PATH", hermes / ".env")
    monkeypatch.setattr("alpha_os.config.OPENCLAW_HOME", tmp_path / ".openclaw")
    monkeypatch.setattr("alpha_os.config.OPENCLAW_ENV_PATH", tmp_path / ".openclaw" / ".env")
    monkeypatch.delenv("ALPHA_OS_PORT", raising=False)
    monkeypatch.delenv("ALPHA_OS_API_TOKEN", raising=False)

    inject_runtime_env("hermes")

    import os

    assert os.environ["ALPHA_OS_PORT"] == "9090"
    assert os.environ["ALPHA_OS_API_TOKEN"] == "local-token"
    assert os.environ["API_SERVER_KEY"] == "hermes-key"


def test_inject_openclaw_env_primary_for_openclaw_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hermes = tmp_path / ".hermes"
    hermes.mkdir()
    (hermes / ".env").write_text("ALPHA_OS_PORT=8080\n", encoding="utf-8")

    openclaw = tmp_path / ".openclaw"
    openclaw.mkdir()
    (openclaw / ".env").write_text(
        "OPENCLAW_GATEWAY_TOKEN=oc-token\n"
        "ALPHA_OS_PORT=4000\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("alpha_os.config.HERMES_HOME", hermes)
    monkeypatch.setattr("alpha_os.config.HERMES_ENV_PATH", hermes / ".env")
    monkeypatch.setattr("alpha_os.config.OPENCLAW_HOME", openclaw)
    monkeypatch.setattr("alpha_os.config.OPENCLAW_ENV_PATH", openclaw / ".env")
    monkeypatch.setattr("alpha_os.config.openclaw_env_paths", lambda: [openclaw / ".env"])
    monkeypatch.delenv("ALPHA_OS_PORT", raising=False)
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)

    inject_runtime_env("openclaw")

    import os

    assert os.environ["ALPHA_OS_PORT"] == "4000"
    assert os.environ["OPENCLAW_GATEWAY_TOKEN"] == "oc-token"


def test_read_openclaw_env_parses_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    openclaw = tmp_path / ".openclaw"
    openclaw.mkdir()
    (openclaw / ".env").write_text('OPENCLAW_GATEWAY_TOKEN="secret"\n', encoding="utf-8")
    monkeypatch.setattr("alpha_os.config.OPENCLAW_HOME", openclaw)
    monkeypatch.setattr("alpha_os.config.OPENCLAW_ENV_PATH", openclaw / ".env")
    monkeypatch.setattr("alpha_os.config.openclaw_env_paths", lambda: [openclaw / ".env"])

    env = read_openclaw_env()
    assert env["OPENCLAW_GATEWAY_TOKEN"] == "secret"


def test_runtime_env_sources_marks_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openclaw = tmp_path / ".openclaw"
    openclaw.mkdir()
    (openclaw / ".env").write_text("ALPHA_OS_PORT=3001\n", encoding="utf-8")
    monkeypatch.setattr("alpha_os.config.HERMES_HOME", tmp_path / ".hermes")
    monkeypatch.setattr("alpha_os.config.HERMES_ENV_PATH", tmp_path / ".hermes" / ".env")
    monkeypatch.setattr("alpha_os.config.OPENCLAW_HOME", openclaw)
    monkeypatch.setattr("alpha_os.config.OPENCLAW_ENV_PATH", openclaw / ".env")
    monkeypatch.setattr("alpha_os.config.openclaw_env_paths", lambda: [openclaw / ".env"])

    sources = runtime_env_sources("openclaw")
    oc = next(s for s in sources if s["runtime"] == "openclaw")
    assert oc["primary"] is True
    assert oc["exists"] is True