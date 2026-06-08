"""Unit tests for Alpha orchestrator."""

from __future__ import annotations

from alpha_os.core.alpha import Alpha


def test_generate_reply_greeting() -> None:
    alpha = Alpha()
    reply = alpha.generate_reply("hello there")
    assert "Good day" in reply


def test_generate_reply_help() -> None:
    alpha = Alpha()
    reply = alpha.generate_reply("help me")
    assert "relay" in reply.lower()


def test_generate_reply_empty() -> None:
    alpha = Alpha()
    assert "service" in alpha.generate_reply("").lower()


def test_process_records_memory() -> None:
    alpha = Alpha()
    reply = alpha.process("status report")
    assert reply
    summary = alpha.memory.to_summary()
    assert summary["history_length"] >= 2


def test_dashboard_state_offline_empty_greeting() -> None:
    alpha = Alpha()
    state = alpha.get_dashboard_state(runtime="offline")
    assert state["greeting"] == ""
    assert state["runtime"] == "offline"
    assert state["agents"] == []


def test_dashboard_state_hermes_connected() -> None:
    alpha = Alpha()
    agents = [{"name": "Forge", "status": "Ready"}]
    state = alpha.get_dashboard_state(hermes_agents=agents, runtime="hermes")
    assert state["agents"] == agents
    assert "instructions" in state["greeting"].lower()