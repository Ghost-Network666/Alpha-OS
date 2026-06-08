"""Tests for stdio MCP discovery from Hermes/OpenClaw configs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha_os.integrations.mcp_discovery import (
    config_paths_status,
    discover_mcp_servers,
)


@pytest.fixture
def hermes_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "hermes_user"
    hermes = home / ".hermes"
    hermes.mkdir(parents=True)
    monkeypatch.setattr(
        "alpha_os.integrations.mcp_discovery.HERMES_HOME",
        hermes,
    )
    monkeypatch.setattr(
        "alpha_os.integrations.mcp_discovery.HERMES_CONFIG_PATHS",
        (hermes / "config.yaml",),
    )
    return hermes


@pytest.fixture
def openclaw_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "openclaw_user"
    oc = home / ".openclaw"
    oc.mkdir(parents=True)
    monkeypatch.setattr(
        "alpha_os.integrations.mcp_discovery.OPENCLAW_HOME",
        oc,
    )
    monkeypatch.setattr(
        "alpha_os.integrations.mcp_discovery.OPENCLAW_CONFIG_PATHS",
        (oc / "openclaw.json",),
    )
    return oc


def test_discover_hermes_stdio_servers(hermes_home: Path) -> None:
    (hermes_home / "config.yaml").write_text(
        """
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    env:
      FOO: bar
  disabled_srv:
    command: echo
    enabled: false
  remote_only:
    url: https://example.com/mcp
""",
        encoding="utf-8",
    )
    servers = discover_mcp_servers("hermes")
    assert len(servers) == 2
    fs = next(s for s in servers if s["name"] == "filesystem")
    assert fs["transport"] == "stdio"
    assert fs["probeable"] is True
    assert fs["command"] == "npx"
    assert fs["env"]["FOO"] == "bar"
    assert fs["source"] == "hermes"

    remote = next(s for s in servers if s["name"] == "remote_only")
    assert remote["probeable"] is False
    assert remote["url"] == "https://example.com/mcp"


def test_discover_openclaw_stdio_servers(openclaw_home: Path) -> None:
    (openclaw_home / "openclaw.json").write_text(
        json.dumps(
            {
                "mcp": {
                    "servers": {
                        "docs": {
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-fetch"],
                        },
                        "stripe": {
                            "url": "https://mcp.stripe.com",
                            "transport": "streamable-http",
                            "auth": "oauth",
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    servers = discover_mcp_servers("openclaw")
    assert len(servers) == 2
    stdio = next(s for s in servers if s["name"] == "docs")
    assert stdio["probeable"] is True
    assert stdio["source"] == "openclaw"

    remote = next(s for s in servers if s["name"] == "stripe")
    assert remote["probeable"] is False
    assert remote["auth"] == "oauth"


def test_runtime_filter_prefers_active_config(
    hermes_home: Path,
    openclaw_home: Path,
) -> None:
    (hermes_home / "config.yaml").write_text(
        "mcp_servers:\n  hermes_only:\n    command: echo\n",
        encoding="utf-8",
    )
    (openclaw_home / "openclaw.json").write_text(
        json.dumps({"mcp": {"servers": {"oc_only": {"command": "echo"}}}}),
        encoding="utf-8",
    )

    hermes_servers = discover_mcp_servers("hermes")
    assert [s["name"] for s in hermes_servers] == ["hermes_only"]

    oc_servers = discover_mcp_servers("openclaw")
    assert [s["name"] for s in oc_servers] == ["oc_only"]

    all_servers = discover_mcp_servers("auto")
    names = {s["name"] for s in all_servers}
    assert names == {"hermes_only", "oc_only"}


def test_config_paths_status_reports_existence(hermes_home: Path) -> None:
    paths = config_paths_status()
    hermes_row = next(p for p in paths if p["runtime"] == "hermes")
    assert hermes_row["key"] == "mcp_servers"
    assert hermes_row["exists"] is False

    (hermes_home / "config.yaml").write_text("mcp_servers: {}\n", encoding="utf-8")
    paths = config_paths_status()
    hermes_row = next(p for p in paths if p["runtime"] == "hermes")
    assert hermes_row["exists"] is True