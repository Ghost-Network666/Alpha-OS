"""Tests for MCP config file watcher."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from alpha_os.integrations.mcp_watcher import mcp_config_watch_loop


@pytest.mark.asyncio
async def test_watcher_triggers_refresh_on_mtime_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("mcp_servers: {}\n", encoding="utf-8")

    calls: list[str] = []

    async def refresh() -> None:
        calls.append("refresh")

    monkeypatch.setattr(
        "alpha_os.integrations.mcp_watcher.discovery_sources",
        lambda: [str(cfg)],
    )

    task = asyncio.create_task(mcp_config_watch_loop(refresh, interval=0.05))
    await asyncio.sleep(0.12)
    assert calls == []

    cfg.write_text("mcp_servers:\n  fs:\n    command: echo\n", encoding="utf-8")
    await asyncio.sleep(0.2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert calls == ["refresh"]