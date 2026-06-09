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


def human_activity_text(source: str, raw: dict[str, Any]) -> str:
    """Short, user-facing line for agent profile cards."""
    if source == "command":
        text = str(raw.get("text") or "").strip()
        return f"Running: {text[:72]}" if text else "Processing your command…"

    if source == "voice":
        text = str(raw.get("text") or "").strip()
        return f"Voice command: {text[:64]}" if text else "Listening / responding…"

    if source == "openclaw":
        ev = str(raw.get("event") or raw.get("type") or "activity")
        payload = raw.get("payload") or raw.get("data") or {}
        if isinstance(payload, dict):
            detail = (
                payload.get("message")
                or payload.get("text")
                or payload.get("tool")
                or payload.get("name")
                or payload.get("action")
                or ""
            )
            if detail:
                return f"{ev}: {str(detail)[:72]}"
        return ev[:80]

    if source == "hermes":
        tool = raw.get("tool") or raw.get("tool_name") or raw.get("function")
        if tool:
            args = raw.get("arguments") or raw.get("input") or ""
            if args and not isinstance(args, str):
                args = str(args)[:40]
            args_s = str(args).strip()[:48] if args else ""
            return f"Tool {tool}{f' — {args_s}' if args_s else ''}"

        status = str(raw.get("status") or raw.get("state") or "").strip().lower()
        msg = (
            raw.get("message")
            or raw.get("text")
            or raw.get("input")
            or raw.get("content")
            or raw.get("output")
            or ""
        )
        msg_s = str(msg).strip()
        ev = str(raw.get("type") or raw.get("event") or "run").strip()

        if status in ("running", "in_progress", "active", "started"):
            if msg_s:
                return f"Working: {msg_s[:72]}"
            return f"{ev} in progress…"
        if status in ("completed", "done", "success"):
            if msg_s:
                return f"Finished: {msg_s[:64]}"
            return "Run completed"
        if status in ("failed", "error", "cancelled"):
            err = raw.get("error") or msg_s or status
            return f"Error: {str(err)[:72]}"
        if msg_s:
            return msg_s[:80]
        if status:
            return f"{ev} — {status}"[:80]
        return _summarize_event(source, raw)

    return _summarize_event(source, raw)


def _profile_hint(raw: dict[str, Any]) -> str | None:
    for key in ("profile", "agent", "agent_id", "profile_name", "session_id"):
        val = raw.get(key)
        if val:
            return str(val).strip().lower()
    return None


class ProfileActivityTracker:
    """Last known activity per Hermes profile (for dashboard agent row)."""

    def __init__(self, ttl_sec: float = 120.0):
        self._ttl = ttl_sec
        self._by_profile: dict[str, dict[str, Any]] = {}

    def record(
        self,
        profile: str,
        source: str,
        raw: dict[str, Any],
        *,
        busy: bool | None = None,
    ) -> None:
        key = str(profile).strip().lower()
        if not key:
            return
        text = human_activity_text(source, raw)
        if not text:
            return
        if busy is None:
            status = str(raw.get("status") or raw.get("state") or "").lower()
            busy = source in ("command", "voice") or status in (
                "running",
                "in_progress",
                "active",
                "started",
            )
        self._by_profile[key] = {
            "text": text,
            "ts": time.time(),
            "busy": bool(busy),
            "source": source,
        }

    def record_event(
        self,
        source: str,
        raw: dict[str, Any],
        *,
        fallback_profile: str | None = None,
    ) -> None:
        hint = _profile_hint(raw) or (
            str(fallback_profile).strip().lower() if fallback_profile else None
        )
        if hint:
            self.record(hint, source, raw)

    def get(self, profile: str) -> dict[str, Any] | None:
        key = str(profile).strip().lower()
        entry = self._by_profile.get(key)
        if not entry:
            return None
        if time.time() - float(entry.get("ts", 0)) > self._ttl:
            self._by_profile.pop(key, None)
            return None
        return entry

    def clear(self) -> None:
        self._by_profile.clear()


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