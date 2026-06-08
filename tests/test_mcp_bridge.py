"""Tests for MCP registry panel data."""

from __future__ import annotations

import pytest

from alpha_os.integrations.mcp_bridge import MCPBridge, MCPRegistry


def test_remote_server_not_probeable() -> None:
    bridge = MCPBridge(
        {
            "name": "stripe",
            "transport": "streamable-http",
            "probeable": False,
            "url": "https://mcp.stripe.com",
            "source": "openclaw",
            "config_path": "/tmp/openclaw.json",
        }
    )
    data = bridge.to_dict()
    assert data["probeable"] is False
    assert data["status"] == "configured"
    assert data["url"] == "https://mcp.stripe.com"
    assert "command" not in data


@pytest.mark.asyncio
async def test_registry_empty_runtime_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "alpha_os.integrations.mcp_bridge.discover_mcp_servers",
        lambda runtime=None: [],
    )
    monkeypatch.setattr(
        "alpha_os.integrations.mcp_bridge.config_paths_status",
        lambda: [
            {
                "runtime": "hermes",
                "path": "/home/u/.hermes/config.yaml",
                "exists": False,
                "key": "mcp_servers",
            }
        ],
    )
    registry = MCPRegistry()
    data = await registry.refresh("hermes")
    assert data["server_count"] == 0
    assert "mcp_servers" in (data.get("error") or "")
    assert data["runtime"] == "hermes"


@pytest.mark.asyncio
async def test_registry_lists_remote_without_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "alpha_os.integrations.mcp_bridge.discover_mcp_servers",
        lambda runtime=None: [
            {
                "name": "remote_api",
                "transport": "streamable-http",
                "probeable": False,
                "url": "https://example.com/mcp",
                "source": "hermes",
                "config_path": "/home/u/.hermes/config.yaml",
                "note": "runtime managed",
            }
        ],
    )
    monkeypatch.setattr(
        "alpha_os.integrations.mcp_bridge.config_paths_status",
        lambda: [],
    )
    registry = MCPRegistry()
    data = await registry.refresh("hermes")
    assert data["server_count"] == 1
    assert data["remote_count"] == 1
    assert data["stdio_count"] == 0
    assert data["connected"] is True
    assert data["servers"][0]["name"] == "remote_api"