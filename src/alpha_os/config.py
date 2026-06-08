"""Alpha OS user configuration — stored in ~/.alpha-os/config.yaml."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from alpha_os.runtime_env import hermes_profile_dir, hermes_profile_name, hermes_root, openclaw_home

CONFIG_DIR = Path(os.getenv("ALPHA_OS_HOME", Path.home() / ".alpha-os"))
CONFIG_PATH = CONFIG_DIR / "config.yaml"


def hermes_home() -> Path:
    return hermes_root()


def hermes_config_path_global() -> Path:
    return hermes_home() / "config.yaml"


def hermes_env_path_global() -> Path:
    return hermes_home() / ".env"


# Back-compat for imports expecting module-level paths (resolved once at import).
HERMES_HOME = hermes_home()
HERMES_CONFIG_PATH = hermes_config_path_global()
HERMES_ENV_PATH = hermes_env_path_global()


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


def active_hermes_profile() -> str:
    override = hermes_profile_name()
    if override:
        return override
    path = hermes_home() / "active_profile"
    if path.exists():
        try:
            name = path.read_text(encoding="utf-8").strip()
            if name:
                return name
        except Exception:
            pass
    return "default"


def list_hermes_profiles() -> list[str]:
    """Profile names under ~/.hermes/profiles with a config.yaml."""
    names: list[str] = []
    root = hermes_home() / "profiles"
    if root.is_dir():
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and (entry / "config.yaml").is_file():
                names.append(entry.name)
    active = active_hermes_profile()
    if active and active not in names:
        names.insert(0, active)
    return names or ["default"]


def set_active_hermes_profile(name: str) -> None:
    name = (name or "").strip() or "default"
    home = hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "active_profile").write_text(f"{name}\n", encoding="utf-8")


def hermes_config_path(profile: str | None = None) -> Path:
    """Active Hermes profile config when present, else ~/.hermes/config.yaml."""
    profile_dir = hermes_profile_dir()
    if profile_dir is not None:
        return profile_dir / "config.yaml"

    name = profile or active_hermes_profile()
    if name and name != "default":
        profile_cfg = hermes_home() / "profiles" / name / "config.yaml"
        if profile_cfg.exists():
            return profile_cfg
        return profile_cfg
    return hermes_config_path_global()


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_hermes_config() -> dict[str, Any]:
    """Read active profile Hermes config (what the gateway actually uses)."""
    return _read_yaml(hermes_config_path())


def write_hermes_config(data: dict[str, Any], *, profile: str | None = None) -> None:
    path = hermes_config_path(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def _merge_env_file(env_path: Path, keys: dict[str, str]) -> None:
    """Merge key=value pairs into a .env file (creates file if needed)."""
    existing: dict[str, str] = {}
    lines: list[str] = []
    if env_path.exists():
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                k, _, v = stripped.partition("=")
                existing[k.strip()] = v.strip().strip('"').strip("'")
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

    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def profile_hermes_env_path(profile: str | None = None) -> Path:
    name = profile or active_hermes_profile()
    return hermes_home() / "profiles" / name / ".env"


def set_hermes_env(keys: dict[str, str], *, profile: str | None = None) -> None:
    """Merge key=value pairs into ~/.hermes/.env and the active profile .env."""
    global_env = hermes_env_path_global()
    _merge_env_file(global_env, keys)
    profile_path = profile_hermes_env_path(profile)
    if profile_path != global_env:
        _merge_env_file(profile_path, keys)


def read_hermes_env() -> dict[str, str]:
    """Prefer active profile .env, fall back to global ~/.hermes/.env."""
    profile_env = profile_hermes_env_path()
    global_env = hermes_env_path_global()
    paths = [profile_env, global_env] if profile_env.exists() else [global_env]
    out: dict[str, str] = {}
    for env_path in paths:
        if not env_path.exists():
            continue
        try:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            pass
    return out


def read_openclaw_config() -> dict[str, Any]:
    home = openclaw_home()
    yaml_cfg = _read_yaml(home / "config.yaml")
    if yaml_cfg:
        return yaml_cfg
    for name in ("openclaw.json", "clawdbot.json", "moltbot.json"):
        path = home / name
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def read_openclaw_env() -> dict[str, str]:
    """Read ~/.openclaw/.env when present."""
    env_path = openclaw_home() / ".env"
    out: dict[str, str] = {}
    if not env_path.exists():
        return out
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass
    return out