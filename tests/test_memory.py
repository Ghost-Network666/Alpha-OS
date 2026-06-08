"""Unit tests for in-memory Alpha memory."""

from __future__ import annotations

from alpha_os.core.memory import AlphaMemory


def test_add_turn_and_summary() -> None:
    mem = AlphaMemory(max_history=10)
    mem.add_turn("user", "hello")
    mem.add_turn("alpha", "hi sir")

    summary = mem.to_summary()
    assert summary["history_length"] == 2
    assert len(summary["recent"]) == 2
    assert summary["recent"][0]["who"] == "user"


def test_trim_history() -> None:
    mem = AlphaMemory(max_history=3)
    for i in range(5):
        mem.add_turn("user", f"msg-{i}")
    assert mem.to_summary()["history_length"] == 3


def test_world_state_updates() -> None:
    mem = AlphaMemory()
    mem.update_agent_status("Forge", "ACTIVE")
    mem.set_metric("events", 12)
    mem.update_tailscale(hostname="alpha-box")

    summary = mem.to_summary()
    assert summary["world"]["active_agents"]["Forge"] == "ACTIVE"
    assert "events" in summary["world"]["metrics_keys"]
    assert summary["world"]["tailscale"]["hostname"] == "alpha-box"