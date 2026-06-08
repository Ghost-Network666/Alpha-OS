"""Unit tests for config load/save and dotenv writers."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from alpha_os.config import (
    get,
    load_config,
    save_config,
    set_hermes_env,
    set_key,
    set_openclaw_env,
)


@pytest.fixture
def config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    alpha_home = tmp_path / "alpha-os"
    alpha_home.mkdir()
    monkeypatch.setattr("alpha_os.config.CONFIG_DIR", alpha_home)
    monkeypatch.setattr("alpha_os.config.CONFIG_PATH", alpha_home / "config.yaml")
    return alpha_home


def test_load_save_and_get_nested_key(
    config_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save_config({"runtime": "hermes", "server": {"port": 9090}})
    cfg = load_config()
    assert cfg["runtime"] == "hermes"
    assert get("server.port") == 9090
    assert get("missing.key", "fallback") == "fallback"


def test_set_key_updates_nested_path(config_home: Path) -> None:
    set_key("hermes.gateway_url", "http://127.0.0.1:8642")
    assert get("hermes.gateway_url") == "http://127.0.0.1:8642"
    raw = yaml.safe_load((config_home / "config.yaml").read_text())
    assert raw["hermes"]["gateway_url"] == "http://127.0.0.1:8642"


def test_set_hermes_env_merges_without_dropping_comments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hermes = tmp_path / ".hermes"
    hermes.mkdir()
    env_path = hermes / ".env"
    env_path.write_text("# gateway\nAPI_SERVER_KEY=old\n", encoding="utf-8")
    monkeypatch.setattr("alpha_os.config.HERMES_HOME", hermes)
    monkeypatch.setattr("alpha_os.config.HERMES_ENV_PATH", env_path)

    set_hermes_env({"API_SERVER_KEY": "new-key", "ALPHA_OS_PORT": "8080"})

    text = env_path.read_text(encoding="utf-8")
    assert "# gateway" in text
    assert "API_SERVER_KEY=new-key" in text
    assert "ALPHA_OS_PORT=8080" in text


def test_set_openclaw_env_writes_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openclaw = tmp_path / ".openclaw"
    openclaw.mkdir()
    env_path = openclaw / ".env"
    monkeypatch.setattr("alpha_os.config.OPENCLAW_HOME", openclaw)
    monkeypatch.setattr("alpha_os.config.OPENCLAW_ENV_PATH", env_path)
    monkeypatch.setattr("alpha_os.config.openclaw_env_paths", lambda: [env_path])

    set_openclaw_env({"OPENCLAW_GATEWAY_TOKEN": "tok", "ALPHA_OS_PORT": "4000"})

    text = env_path.read_text(encoding="utf-8")
    assert "OPENCLAW_GATEWAY_TOKEN=tok" in text
    assert "ALPHA_OS_PORT=4000" in text