"""SQLite-backed persistent memory."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from .memory import AlphaMemory, ConversationTurn, WorldState

DB_PATH = Path(os.getenv("ALPHA_DB_PATH", Path.home() / ".alpha-os" / "memory.db"))


class PersistentMemory:
    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self.world = self._load_world()
        self.session_started = datetime.now(UTC).isoformat()

    def _init_db(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL,
                meta TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS world_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        self._conn.commit()

    def _load_world(self) -> WorldState:
        ws = WorldState()
        cur = self._conn.execute("SELECT key, value FROM world_state")
        for row in cur.fetchall():
            try:
                val = json.loads(row["value"])
                if row["key"] == "tailscale":
                    ws.tailscale.update(val)
                elif row["key"] == "active_agents":
                    ws.active_agents.update(val)
                elif row["key"] == "recent_metrics":
                    ws.recent_metrics.update(val)
            except Exception:
                pass
        return ws

    def _save_world_key(self, key: str, value: Any):
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """INSERT INTO world_state(key, value, updated_at)
               VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET
               value=excluded.value, updated_at=excluded.updated_at""",
            (key, json.dumps(value), now),
        )
        self._conn.commit()

    def add_turn(self, speaker: str, text: str, meta: Optional[Dict] = None):
        now = datetime.now(UTC).isoformat(timespec="seconds")
        self._conn.execute(
            "INSERT INTO turns(timestamp,speaker,text,meta) VALUES(?,?,?,?)",
            (now, speaker, text, json.dumps(meta or {})),
        )
        self._conn.commit()
        self._conn.execute(
            """DELETE FROM turns WHERE id NOT IN (
                 SELECT id FROM turns ORDER BY id DESC LIMIT ?
               )""",
            (self.max_history,),
        )
        self._conn.commit()

    def get_recent(self, n: int = 12) -> List[ConversationTurn]:
        cur = self._conn.execute(
            """SELECT timestamp, speaker, text, meta
               FROM turns ORDER BY id DESC LIMIT ?""",
            (n,),
        )
        rows = cur.fetchall()
        rows = list(reversed(rows))
        return [
            ConversationTurn(
                timestamp=r["timestamp"],
                speaker=r["speaker"],
                text=r["text"],
                meta=json.loads(r["meta"] or "{}"),
            )
            for r in rows
        ]

    def update_agent_status(self, agent: str, status: str):
        self.world.active_agents[agent] = status
        self._save_world_key("active_agents", self.world.active_agents)

    def set_metric(self, key: str, value: Any):
        self.world.recent_metrics[key] = value
        self._save_world_key("recent_metrics", self.world.recent_metrics)

    def update_tailscale(self, **kwargs):
        self.world.tailscale.update(kwargs)
        self._save_world_key("tailscale", self.world.tailscale)

    def to_summary(self) -> Dict[str, Any]:
        total = self._conn.execute(
            "SELECT COUNT(*) as c FROM turns"
        ).fetchone()["c"]
        return {
            "session_started": self.session_started,
            "history_length": total,
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

    def close(self):
        self._conn.close()