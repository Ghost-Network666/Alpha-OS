"""Unit tests for live event buffer."""

from __future__ import annotations

import time

from alpha_os.core.events import (
    LiveEventBuffer,
    ProfileActivityTracker,
    _summarize_event,
    human_activity_text,
)


def test_summarize_openclaw_event_with_payload() -> None:
    summary = _summarize_event(
        "openclaw",
        {"event": "message", "payload": {"text": "hello world"}},
    )
    assert "message" in summary
    assert "hello" in summary


def test_summarize_hermes_event() -> None:
    summary = _summarize_event(
        "hermes",
        {"type": "run", "status": "completed", "run_id": "abc123"},
    )
    assert "run" in summary
    assert "completed" in summary


def test_live_event_buffer_push_and_recent() -> None:
    buf = LiveEventBuffer(max_events=5)
    buf.push("hermes", {"type": "ping"})
    buf.push("openclaw", {"event": "tick"})

    recent = buf.get_recent(10)
    assert len(recent) == 2
    assert recent[0]["source"] == "hermes"
    assert recent[1]["source"] == "openclaw"
    assert buf.latest_seq() == 2


def test_live_event_buffer_trims_to_max() -> None:
    buf = LiveEventBuffer(max_events=3)
    for i in range(5):
        buf.push("hermes", {"type": f"e{i}"})
    assert len(buf.get_recent(10)) == 3
    assert buf.latest_seq() == 5


def test_consume_pulse_and_events_per_minute() -> None:
    buf = LiveEventBuffer()
    buf.push("voice", {"type": "wake"})
    assert buf.consume_pulse() is True
    assert buf.consume_pulse() is False

    old = time.time() - 120
    buf._events[0]["ts"] = old  # type: ignore[index]
    buf.push("hermes", {"type": "fresh"})
    assert buf.events_per_minute() == 1


def test_human_activity_command() -> None:
    text = human_activity_text("command", {"text": "check polymarket positions"})
    assert "Running:" in text
    assert "polymarket" in text


def test_human_activity_hermes_tool() -> None:
    text = human_activity_text(
        "hermes",
        {"type": "tool_call", "tool": "web_search", "status": "running"},
    )
    assert "web_search" in text


def test_profile_activity_tracker() -> None:
    tracker = ProfileActivityTracker(ttl_sec=60)
    tracker.record_event(
        "command",
        {"text": "summarize inbox"},
        fallback_profile="alpha",
    )
    entry = tracker.get("alpha")
    assert entry is not None
    assert "summarize" in entry["text"]
    assert entry["busy"] is True
    assert tracker.get("rewards") is None