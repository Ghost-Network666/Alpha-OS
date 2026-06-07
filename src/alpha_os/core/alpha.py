"""Alpha — British butler orchestrator."""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

logger = logging.getLogger("alpha_os")


class Alpha:
    def __init__(self):
        try:
            from .persistent_memory import PersistentMemory
            self.memory = PersistentMemory()
        except Exception as e:
            logger.warning("PersistentMemory unavailable (%s), using in-memory", e)
            from .memory import AlphaMemory
            self.memory = AlphaMemory()

        self._demo_agents = self._load_demo_agents()

    def _load_demo_agents(self) -> list[dict[str, Any]]:
        if os.getenv("ALPHA_STANDALONE_DEMO") != "1":
            return []
        try:
            from alpha_os.agents import DEMO_AGENTS
            return DEMO_AGENTS
        except Exception:
            return []

    def process(self, command: str) -> str:
        command = (command or "").strip()
        if not command:
            return "At your service, sir. How may I assist?"
        self.memory.add_turn("user", command)
        lower = command.lower()
        if any(w in lower for w in ("hello", "hi", "greet", "good morning")):
            reply = (
                "Good day. Alpha OS is online and awaiting your instructions, sir."
            )
        elif "status" in lower:
            reply = "All systems nominal. Awaiting live gateway data, sir."
        elif "help" in lower:
            reply = (
                "I can relay commands to your Hermes or OpenClaw runtime, "
                "monitor agents, and keep session history. Simply state your intent."
            )
        else:
            reply = (
                f"Understood: \"{command[:80]}\". "
                "I shall relay this to the connected runtime when live, sir."
            )
        self.memory.add_turn("alpha", reply)
        return reply

    def get_dashboard_state(
        self,
        hermes_agents: Optional[List[dict]] = None,
        runtime: str = "offline",
    ) -> dict[str, Any]:
        agents = []
        if hermes_agents:
            agents = hermes_agents
        elif self._demo_agents:
            agents = self._demo_agents
        else:
            agents = [{
                "name": "Alpha",
                "title": "Awaiting gateway",
                "status": "Ready",
                "color": "#ff2a6d",
            }]

        return {
            "agents": agents,
            "memory": self.memory.to_summary(),
            "style": {
                "theme": "cyber",
                "accent": "#00f0ff",
                "orb": "#ff2a6d",
            },
            "view": "full",
            "greeting": "Alpha OS online. Connect your Hermes or OpenClaw gateway to begin.",
            "hermes_connected": False,
            "runtime": runtime,
        }