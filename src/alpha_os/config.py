"""Alpha OS user configuration — stored in ~/.alpha-os/config.yaml."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import yaml

CONFIG_DIR = Path(os.getenv("ALPHA_OS_HOME", Path.home() / ".alpha-os"))
CONFIG_PATH = CONFIG_DIR / "config.yaml"


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config(data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def get(key: str, default: Any = None) -> Any:
    cfg = load_config()
    parts = key.split(".")
    cur: Any = cfg
    for p in parts:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
        if cur is None:
            return default
    return cur


def set_key(key: str, value: Any) -> None:
    cfg = load_config()
    parts = key.split(".")
    cur = cfg
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value
    save_config(cfg)


def read_hermes_env() -> dict[str, str]:
    env_path = Path.home() / ".hermes" / ".env"
    out: dict[str, str] = {}
    if not env_path.exists():
        return out
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return out


def read_openclaw_config() -> dict[str, Any]:
    for name in ("openclaw.json", "clawdbot.json", "moltbot.json"):
        path = Path.home() / ".openclaw" / name
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
    return {}