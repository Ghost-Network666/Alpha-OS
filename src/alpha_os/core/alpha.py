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

    def generate_reply(self, command: str) -> str:
        command = (command or "").strip()
        if not command:
            return "At your service, sir. How may I assist?"
        lower = command.lower()
        if any(w in lower for w in ("hello", "hi", "greet", "good morning")):
            return "Good day. Alpha OS is online and awaiting your instructions, sir."
        if "status" in lower:
            return "All systems nominal. Awaiting live gateway data, sir."
        if "help" in lower:
            return (
                "I can relay commands to your Hermes or OpenClaw runtime, "
                "monitor agents, and keep session history. Simply state your intent."
            )
        return (
            f"Understood: \"{command[:80]}\". "
            "I shall relay this to the connected runtime when live, sir."
        )

    def process(self, command: str) -> str:
        command = (command or "").strip()
        if not command:
            return "At your service, sir. How may I assist?"
        self.memory.add_turn("user", command)
        reply = self.generate_reply(command)
        self.memory.add_turn("alpha", reply)
        return reply

    def get_dashboard_state(
        self,
        hermes_agents: Optional[List[dict]] = None,
        runtime: str = "offline",
    ) -> dict[str, Any]:
        agents: list[dict[str, Any]] = []
        if hermes_agents:
            agents = hermes_agents
        elif self._demo_agents:
            agents = self._demo_agents

        connected = runtime == "hermes" and bool(hermes_agents is not None)
        greeting = (
            "Gateway connected. Awaiting your instructions, sir."
            if connected
            else ""
        )

        return {
            "agents": agents,
            "memory": {"recent": [], "history_length": 0} if not connected else self.memory.to_summary(),
            "style": {
                "theme": "cyber",
                "accent": "#00f5ff",
                "orb": "#ff2d78",
            },
            "view": "full",
            "greeting": greeting,
            "hermes_connected": False,
            "runtime": runtime,
        }