"""In-memory conversation and world state (fallback when SQLite unavailable)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional


@dataclass
class ConversationTurn:
    timestamp: str
    speaker: str
    text: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldState:
    tailscale: Dict[str, Any] = field(default_factory=dict)
    active_agents: Dict[str, str] = field(default_factory=dict)
    recent_metrics: Dict[str, Any] = field(default_factory=dict)


class AlphaMemory:
    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        self._turns: List[ConversationTurn] = []
        self.world = WorldState()
        self.session_started = datetime.now(UTC).isoformat()

    def add_turn(self, speaker: str, text: str, meta: Optional[Dict] = None):
        self._turns.append(ConversationTurn(
            timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
            speaker=speaker,
            text=text,
            meta=meta or {},
        ))
        if len(self._turns) > self.max_history:
            self._turns = self._turns[-self.max_history:]

    def get_recent(self, n: int = 12) -> List[ConversationTurn]:
        return self._turns[-n:]

    def update_agent_status(self, agent: str, status: str):
        self.world.active_agents[agent] = status

    def set_metric(self, key: str, value: Any):
        self.world.recent_metrics[key] = value

    def update_tailscale(self, **kwargs):
        self.world.tailscale.update(kwargs)

    def to_summary(self) -> Dict[str, Any]:
        return {
            "session_started": self.session_started,
            "history_length": len(self._turns),
            "recent": [
                {"t": t.timestamp, "who": t.speaker, "text": t.text[:140]}
                for t in self.get_recent(6)
            ],
            "world": {
                "active_agents": self.world.active_agents,
                "tailscale": self.world.tailscale,
                "metrics_keys": list(self.world.recent_metrics.keys()),
            },
        }