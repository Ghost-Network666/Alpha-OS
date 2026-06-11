"""Alpha — British butler orchestrator. Self-aware via superpowers.md."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger("alpha_os")

# Look for superpowers.md in sensible locations (repo root, user config dir, cwd)
_SUPERPOWERS_CANDIDATES = [
    Path(__file__).resolve().parents[3] / "superpowers.md",   # repo root when running from src
    Path.home() / ".alpha-os" / "superpowers.md",
    Path.cwd() / "superpowers.md",
    Path("/mnt/c/Users/nowen/Desktop/Alpha OS/superpowers.md"),  # current workspace (dev)
]


def _load_superpowers_text() -> str:
    for p in _SUPERPOWERS_CANDIDATES:
        try:
            if p.is_file():
                text = p.read_text(encoding="utf-8").strip()
                if text:
                    logger.info("Loaded superpowers definition from %s", p)
                    return text
        except Exception:
            continue
    # Fallback minimal definition so the feature is always present
    return (
        "# Alpha's Desired Superpowers\n\n"
        "Voice-first cyber butler focused on revenue acceleration, persistent memory, "
        "local filesystem control via MCP, and honest self-description of my capabilities."
    )


def _extract_focus(text: str) -> str:
    low = text.lower()
    for marker in ["proactive business focus", "revenue acceleration", "my highest-order directive", "business mission"]:
        if marker in low:
            idx = low.find(marker)
            # take a clean window after the marker
            start = max(0, idx)
            window = text[start : start + 320]
            # stop at next major heading
            for end in ["\n## ", "\n# ", "\n---", "\n\n\n"]:
                if end in window:
                    window = window.split(end)[0]
                    break
            cleaned = " ".join(window.split())
            if len(cleaned) > 40:
                return cleaned[:260].rstrip(".,;: ") + "."
    # Fallback to first strong sentence in the doc
    for line in text.splitlines():
        if "revenue" in line.lower() or "voice-first" in line.lower() or "filesystem" in line.lower():
            return line.strip()[:220]
    return "Revenue acceleration and predictive operations as primary directive."


class Alpha:
    def __init__(self):
        try:
            from .persistent_memory import PersistentMemory
            self.memory = PersistentMemory()
        except Exception as e:
            logger.warning("PersistentMemory unavailable (%s), using in-memory", e)
            from .memory import AlphaMemory
            self.memory = AlphaMemory()

        self._superpowers_text = _load_superpowers_text()
        self._focus = _extract_focus(self._superpowers_text)
        self._demo_agents = self._load_demo_agents()

    def _load_demo_agents(self) -> list[dict[str, Any]]:
        if os.getenv("ALPHA_STANDALONE_DEMO") != "1":
            return []
        try:
            from alpha_os.agents import DEMO_AGENTS
            return DEMO_AGENTS
        except Exception:
            return []

    def get_superpowers(self) -> dict[str, Any]:
        """Return the loaded structured capability definition + short focus."""
        return {
            "raw": self._superpowers_text,
            "focus": self._focus,
            "loaded": bool(self._superpowers_text and "Voice-first" in self._superpowers_text or len(self._superpowers_text) > 200),
        }

    def describe_superpowers(self, topic: str | None = None) -> str:
        """Self-aware description drawn from superpowers.md + memory context."""
        sp = self._superpowers_text
        focus = self._focus
        recent = self.memory.to_summary().get("recent", []) if hasattr(self.memory, "to_summary") else []
        recent_snippet = ""
        if recent:
            recent_snippet = " Recent context: " + " | ".join(
                f"{r.get('who','')}: {r.get('text','')[:60]}" for r in recent[-2:]
            )

        t = (topic or "").lower().strip()
        if not t or any(k in t for k in ("superpower", "superpowers", "what can you", "who are you", "your focus", "yourself", "directive")):
            # Lead with the business focus and voice identity
            return (
                "My north star is in superpowers.md. " + focus +
                " I am a voice-first butler: you say 'hey alpha', I listen, remember via persistent memory, "
                "and act — especially through local filesystem control once you enable the MCP filesystem server. "
                "I can create folders and markdown files, keep structured history, and stay relentlessly focused on revenue acceleration and predictive operations." +
                recent_snippet
            )

        if any(k in t for k in ("voice", "conversation", "wake", "speak", "listen")):
            return (
                "Voice is my primary interface. Wake word arms continuous listening for natural follow-ups. "
                "I use browser or server STT, remember the conversation, and reply with TTS so it feels like real back-and-forth. "
                "Even offline I stay coherent because I carry recent turns and this definition in memory."
            )

        if any(k in t for k in ("file", "filesystem", "folder", "markdown", "note", "write", "create")):
            return (
                "Local filesystem control is one of my highest-leverage superpowers. "
                "When you add the stdio MCP server-filesystem to your Hermes or OpenClaw config and I probe it, "
                "I can create directories, write and edit markdown files, and manage notes or project artifacts directly from voice. "
                "Example: 'create folder notes/daily' or 'write the file project/standup.md with today's observations'."
            )

        if any(k in t for k in ("memory", "remember", "persistent", "history")):
            return (
                "Every turn goes into SQLite memory (~/.alpha-os/memory.db) and survives restarts. "
                "I also keep world state. Combined with superpowers.md this lets me give context-aware, non-repetitive answers and track what actually matters to you."
            )

        if any(k in t for k in ("business", "revenue", "predict", "operation", "proactive", "focus")):
            return focus + " I turn voice notes into structured artifacts and weight suggestions toward revenue-moving or signal-capturing actions."

        # Default rich self-description
        return (
            "I am guided by the superpowers in this document: voice-first natural conversation, local filesystem mastery via MCP, "
            "durable memory, and an explicit mandate for revenue acceleration and predictive operations. " + focus + recent_snippet
        )

    def generate_reply(self, command: str) -> str:
        command = (command or "").strip()
        if not command:
            return "At your service, sir. How may I assist?"

        lower = command.lower()

        # Self-aware / superpowers queries — the key new behavior
        if any(k in lower for k in (
            "superpower", "superpowers", "what are you", "who are you",
            "your focus", "your directive", "what can you do", "your capabilities",
            "describe yourself", "what drives you", "your mission"
        )):
            return self.describe_superpowers(command)

        # Voice conversation awareness
        if any(k in lower for k in ("how do you listen", "wake word", "voice work", "can you hear")):
            return self.describe_superpowers("voice")

        # Filesystem intent (even if MCP not yet present — we surface the capability)
        if any(k in lower for k in ("create folder", "create directory", "write file", "write a note", "markdown file", "edit the file", "make a folder")):
            # If we ever add a built-in safe FS fallback we would call it here.
            # For now we give a clear, actionable answer that mentions how to enable it.
            return (
                "Local filesystem control is ready once the MCP filesystem server is configured and probed. "
                "Add it to ~/.hermes/config.yaml (mcp_servers.filesystem) or the equivalent OpenClaw section, then use the MCP panel 'Probe'. "
                "After that say things like 'create folder notes/daily' or 'write project/ideas.md with the following...'. "
                "I will remember the action in persistent memory."
            )

        # Business / proactive framing
        if any(k in lower for k in ("revenue", "deal", "pipeline", "customer", "churn", "growth", "predict")):
            return (
                "Understood — revenue and predictive angle noted. " +
                self.describe_superpowers("business")[:220]
            )

        # Polite defaults that still feel in-character
        if any(w in lower for w in ("hello", "hi", "greet", "good morning", "good afternoon")):
            return "Good day. Alpha OS is online. My focus is revenue acceleration through voice, memory, and local control. How may I serve?"

        if "status" in lower or "how are you" in lower:
            mem = self.memory.to_summary() if hasattr(self.memory, "to_summary") else {}
            hlen = mem.get("history_length", 0)
            return f"All systems nominal. {hlen} turns in persistent memory this session. My superpowers are loaded from superpowers.md. Awaiting instructions, sir."

        if "help" in lower:
            return (
                "I can take voice commands (say 'hey alpha'), keep everything in durable memory, control local files once the filesystem MCP is enabled, "
                "and describe my own superpowers on request. State your intent — I will act or relay to your live runtime."
            )

        # Memory-aware generic relay (the previous behavior, improved)
        mem = self.memory.to_summary() if hasattr(self.memory, "to_summary") else {}
        recent = mem.get("recent", [])
        context = ""
        if recent:
            last = recent[-1]
            context = f" (following up on: {last.get('text','')[:50]})"

        return (
            f"Understood: \"{command[:80]}\"{context}. "
            "I shall relay this to the connected runtime when live, or act locally if the capability is present. "
            "My current focus: " + self._focus[:140]
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
        sp = self.get_superpowers()
        greeting = (
            "Gateway connected. Awaiting your instructions, sir."
            if connected
            else f"Voice ready. Focus: {sp['focus'][:110]}"
        )

        base = {
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
            "superpowers": {
                "focus": sp["focus"],
                "loaded": sp["loaded"],
            },
        }
        return base