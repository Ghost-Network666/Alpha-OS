"""Alpha OS user configuration — stored in ~/.alpha-os/config.yaml."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(os.getenv("ALPHA_OS_HOME", Path.home() / ".alpha-os"))
CONFIG_PATH = CONFIG_DIR / "config.yaml"
HERMES_HOME = Path.home() / ".hermes"
HERMES_CONFIG_PATH = HERMES_HOME / "config.yaml"
HERMES_ENV_PATH = HERMES_HOME / ".env"
OPENCLAW_HOME = Path.home() / ".openclaw"
OPENCLAW_ENV_PATH = OPENCLAW_HOME / ".env"

_ALPHA_OS_ENV_KEYS = frozenset(
    {
        "ALPHA_OS_PORT",
        "ALPHA_OS_HOST",
        "ALPHA_OS_FRONTEND_PORT",
        "ALPHA_OS_FRONTEND_HOST",
        "ALPHA_OS_WORKERS",
        "ALPHA_OS_API_TOKEN",
        "ALPHA_OS_HOME",
    }
)

_HERMES_INJECT_KEYS = frozenset(
    {
        "HERMES_GATEWAY_URL",
        "HERMES_API_KEY",
        "API_SERVER_KEY",
        "API_SERVER_HOST",
        "API_SERVER_PORT",
        "API_SERVER_ENABLED",
    }
)

_OPENCLAW_INJECT_KEYS = frozenset(
    {
        "OPENCLAW_GATEWAY_URL",
        "OPENCLAW_GATEWAY_TOKEN",
        "OPENCLAW_GATEWAY_PORT",
        "OPENCLAW_HOME",
        "OPENCLAW_STATE_DIR",
        "OPENCLAW_CONFIG_PATH",
    }
)


def _read_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return out


def openclaw_env_paths() -> list[Path]:
    paths: list[Path] = []
    state = os.getenv("OPENCLAW_STATE_DIR", "").strip()
    if state:
        paths.append(Path(state).expanduser() / ".env")
    paths.append(OPENCLAW_ENV_PATH)
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def read_hermes_env() -> dict[str, str]:
    return _read_dotenv(HERMES_ENV_PATH)


def read_openclaw_env() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in openclaw_env_paths():
        merged.update(_read_dotenv(path))
    return merged


def _resolve_primary_runtime(runtime: str | None = None) -> str:
    pref = (runtime or load_config().get("runtime") or "auto").lower()
    if pref in ("hermes", "openclaw"):
        return pref
    if OPENCLAW_HOME.exists() and not HERMES_HOME.exists():
        return "openclaw"
    if HERMES_HOME.exists():
        return "hermes"
    if OPENCLAW_HOME.exists():
        return "openclaw"
    return "auto"


def inject_runtime_env(runtime: str | None = None) -> dict[str, str]:
    """
    Inject env from ~/.hermes/.env and ~/.openclaw/.env.

    Process environment wins for most keys. The primary runtime's dotenv file
    owns ALPHA_OS_* and that runtime's gateway keys when both files exist.
    """
    primary = _resolve_primary_runtime(runtime)
    hermes = read_hermes_env()
    openclaw = read_openclaw_env()
    primary_block = openclaw if primary == "openclaw" else hermes
    force_keys = _ALPHA_OS_ENV_KEYS | _HERMES_INJECT_KEYS | _OPENCLAW_INJECT_KEYS

    for block in (hermes, openclaw):
        for key, value in block.items():
            if not value:
                continue
            if key not in os.environ:
                os.environ[key] = value

    for key, value in primary_block.items():
        if not value:
            continue
        if key in force_keys:
            os.environ[key] = value

    return {**hermes, **openclaw}


def inject_hermes_env() -> dict[str, str]:
    """Backward-compatible alias."""
    return inject_runtime_env()


def runtime_env_sources(runtime: str | None = None) -> list[dict[str, str]]:
    primary = _resolve_primary_runtime(runtime)
    sources: list[dict[str, str]] = []
    if HERMES_ENV_PATH.exists() or HERMES_HOME.exists():
        sources.append(
            {
                "runtime": "hermes",
                "path": str(HERMES_ENV_PATH),
                "exists": HERMES_ENV_PATH.exists(),
                "primary": primary == "hermes",
            }
        )
    for path in openclaw_env_paths():
        sources.append(
            {
                "runtime": "openclaw",
                "path": str(path),
                "exists": path.exists(),
                "primary": primary == "openclaw",
            }
        )
    return sources


def alpha_os_port() -> int:
    inject_runtime_env()
    return int(os.getenv("ALPHA_OS_PORT", "8080"))


def alpha_os_host() -> str:
    inject_runtime_env()
    return str(os.getenv("ALPHA_OS_HOST", "127.0.0.1"))


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


def set_openclaw_env(keys: dict[str, str]) -> None:
    """Merge key=value pairs into ~/.openclaw/.env (creates file if needed)."""
    target = openclaw_env_paths()[-1]
    existing = read_openclaw_env()
    lines: list[str] = []
    if target.exists():
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
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

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(out) + "\n", encoding="utf-8")


def read_openclaw_config() -> dict[str, Any]:
    inject_runtime_env()
    config_path = os.getenv("OPENCLAW_CONFIG_PATH", "").strip()
    candidates: list[Path] = []
    if config_path:
        candidates.append(Path(config_path).expanduser())
    state = os.getenv("OPENCLAW_STATE_DIR", "").strip()
    if state:
        base = Path(state).expanduser()
        candidates.extend(base / name for name in ("openclaw.json", "clawdbot.json", "moltbot.json"))
    candidates.extend(OPENCLAW_HOME / name for name in ("openclaw.json", "clawdbot.json", "moltbot.json"))
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen or not path.exists():
            continue
        seen.add(key)
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            continue
    return {}