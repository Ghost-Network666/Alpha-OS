"""Sync Alpha wake phrase with OpenClaw gateway voicewake settings."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from alpha_os.bridges.detector import openclaw_installed
from alpha_os.voice.wakeword import DEFAULT_WAKE_WORD, normalize_wake_word

OPENCLAW_HOME = Path.home() / ".openclaw"
VOICEWAKE_PATH = OPENCLAW_HOME / "settings" / "voicewake.json"
MAX_TRIGGERS = 32
MAX_TRIGGER_LEN = 64


def voicewake_path() -> Path:
    return VOICEWAKE_PATH


def wake_word_to_triggers(wake_word: str) -> list[str]:
    """Map Alpha wake phrase to OpenClaw trigger list."""
    wake = normalize_wake_word(wake_word)
    if not wake:
        wake = DEFAULT_WAKE_WORD
    triggers = [wake]
    if wake.startswith("hey "):
        tail = wake[4:].strip()
        if tail and tail not in triggers:
            triggers.append(tail)
    return triggers[:MAX_TRIGGERS]


def normalize_triggers(triggers: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in triggers:
        t = (raw or "").strip().lower()
        if not t or len(t) > MAX_TRIGGER_LEN:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= MAX_TRIGGERS:
            break
    return out or wake_word_to_triggers(DEFAULT_WAKE_WORD)


def read_voicewake() -> dict[str, Any]:
    if not VOICEWAKE_PATH.exists():
        return {"triggers": wake_word_to_triggers(DEFAULT_WAKE_WORD), "updatedAtMs": 0}
    try:
        data = json.loads(VOICEWAKE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid voicewake shape")
        triggers = data.get("triggers")
        if not isinstance(triggers, list):
            triggers = []
        return {
            "triggers": normalize_triggers([str(t) for t in triggers]),
            "updatedAtMs": int(data.get("updatedAtMs") or 0),
        }
    except Exception:
        return {"triggers": wake_word_to_triggers(DEFAULT_WAKE_WORD), "updatedAtMs": 0}


def write_voicewake(triggers: list[str]) -> dict[str, Any]:
    normalized = normalize_triggers(triggers)
    payload = {
        "triggers": normalized,
        "updatedAtMs": int(time.time() * 1000),
    }
    VOICEWAKE_PATH.parent.mkdir(parents=True, exist_ok=True)
    VOICEWAKE_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def sync_wake_word_to_openclaw(
    wake_word: str,
    *,
    bridge: Any = None,
) -> dict[str, Any]:
    """Persist wake phrase to ~/.openclaw/settings/voicewake.json and gateway RPC."""
    triggers = wake_word_to_triggers(wake_word)
    file_result = write_voicewake(triggers) if openclaw_installed() else None

    rpc_result: Optional[dict[str, Any]] = None
    if bridge is not None and getattr(bridge, "_connected", False):
        try:
            rpc_result = getattr(bridge, "voicewake_set_sync")(triggers)
        except Exception as exc:
            rpc_result = {"ok": False, "error": str(exc)[:200]}

    return {
        "ok": True,
        "triggers": triggers,
        "path": str(VOICEWAKE_PATH),
        "file_written": file_result is not None,
        "rpc": rpc_result,
    }


def load_wake_word_from_openclaw(default: str = DEFAULT_WAKE_WORD) -> Optional[str]:
    """Read primary trigger from OpenClaw voicewake.json when present."""
    if not openclaw_installed() or not VOICEWAKE_PATH.exists():
        return None
    triggers = read_voicewake().get("triggers") or []
    if not triggers:
        return None
    return str(triggers[0])