"""Ring buffer for live gateway events (Hermes SSE + OpenClaw WS)."""

from __future__ import annotations

import time
from typing import Any


def _summarize_event(source: str, raw: dict[str, Any]) -> str:
    if source == "openclaw":
        ev = raw.get("event", raw.get("type", "event"))
        payload = raw.get("payload") or raw.get("data") or {}
        if isinstance(payload, dict):
            detail = (
                payload.get("message")
                or payload.get("text")
                or payload.get("name")
                or payload.get("id")
                or ""
            )
            if detail:
                return f"{ev}: {str(detail)[:80]}"
        return str(ev)

    if source == "hermes":
        ev_type = raw.get("type") or raw.get("event") or "run"
        run_id = raw.get("run_id") or raw.get("id") or ""
        status = raw.get("status") or raw.get("state") or ""
        parts = [str(ev_type)]
        if status:
            parts.append(str(status))
        if run_id:
            parts.append(str(run_id)[:12])
        return " ".join(parts)

    return str(raw.get("type") or raw.get("event") or "event")[:80]


class LiveEventBuffer:
    def __init__(self, max_events: int = 50):
        self._max = max_events
        self._events: list[dict[str, Any]] = []
        self._seq = 0
        self._pulse = False

    def push(self, source: str, raw: dict[str, Any]) -> None:
        self._seq += 1
        entry = {
            "seq": self._seq,
            "source": source,
            "ts": time.time(),
            "summary": _summarize_event(source, raw),
            "raw": raw,
        }
        self._events.append(entry)
        if len(self._events) > self._max:
            self._events = self._events[-self._max :]
        self._pulse = True

    def get_recent(self, n: int = 20) -> list[dict[str, Any]]:
        return [
            {
                "seq": e["seq"],
                "source": e["source"],
                "ts": e["ts"],
                "summary": e["summary"],
            }
            for e in self._events[-n:]
        ]

    def latest_seq(self) -> int:
        return self._seq

    def consume_pulse(self) -> bool:
        if self._pulse:
            self._pulse = False
            return True
        return False

    @property
    def pulse(self) -> bool:
        return self._pulse

    def events_per_minute(self, window_sec: float = 60.0) -> int:
        cutoff = time.time() - window_sec
        return sum(1 for e in self._events if e.get("ts", 0) >= cutoff)