"""Alpha OS user configuration — stored in ~/.alpha-os/config.yaml."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import yaml

CONFIG_DIR = Path(os.getenv("ALPHA_OS_HOME", Path.home() / ".alpha-os"))
CONFIG_PATH = CONFIG_DIR / "config.yaml"
HERMES_HOME = Path.home() / ".hermes"
HERMES_CONFIG_PATH = HERMES_HOME / "config.yaml"
HERMES_ENV_PATH = HERMES_HOME / ".env"


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


def hermes_config_path() -> Path:
    return HERMES_CONFIG_PATH


def read_hermes_config() -> dict[str, Any]:
    if not HERMES_CONFIG_PATH.exists():
        return {}
    try:
        with open(HERMES_CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_hermes_config(data: dict[str, Any]) -> None:
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    with open(HERMES_CONFIG_PATH, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def set_hermes_env(keys: dict[str, str]) -> None:
    """Merge key=value pairs into ~/.hermes/.env (creates file if needed)."""
    existing = read_hermes_env()
    lines: list[str] = []
    if HERMES_ENV_PATH.exists():
        try:
            lines = HERMES_ENV_PATH.read_text(encoding="utf-8").splitlines()
        except Exception:
            lines = []

    updated = dict(existing)
    updated.update({k: v for k, v in keys.items() if v})

    present = set()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        key, _, _ = stripped.partition("=")
        key = key.strip()
        if key in updated:
            out.append(f"{key}={updated[key]}")
            present.add(key)
        else:
            out.append(line)

    for key, val in updated.items():
        if key not in present:
            out.append(f"{key}={val}")

    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    HERMES_ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def read_hermes_env() -> dict[str, str]:
    env_path = HERMES_ENV_PATH
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