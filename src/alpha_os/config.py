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
    return HERMES_HOME


def hermes_config_path_global() -> Path:
    return hermes_home() / "config.yaml"


def hermes_env_path_global() -> Path:
    return hermes_home() / ".env"


# Back-compat for imports expecting module-level paths (resolved once at import).
HERMES_HOME = hermes_root()
HERMES_CONFIG_PATH = hermes_config_path_global()
HERMES_ENV_PATH = hermes_env_path_global()
OPENCLAW_HOME = openclaw_home()
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


def read_hermes_profile_config(profile: str) -> dict[str, Any]:
    """Read ~/.hermes/profiles/<name>/config.yaml."""
    name = (profile or "").strip()
    if not name:
        return {}
    return _read_yaml(hermes_home() / "profiles" / name / "config.yaml")


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
    _merge_env_file(HERMES_ENV_PATH, keys)
    profile_path = profile_hermes_env_path(profile)
    if profile_path != HERMES_ENV_PATH:
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


def openclaw_env_paths() -> list[Path]:
    paths: list[Path] = []
    state = os.getenv("OPENCLAW_STATE_DIR", "").strip()
    if state:
        paths.append(Path(state).expanduser() / ".env")
    paths.append(OPENCLAW_ENV_PATH)
    seen: set[str] = set()
    out: list[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


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
    """Inject env from ~/.hermes/.env and ~/.openclaw/.env."""
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


def set_openclaw_env(keys: dict[str, str]) -> None:
    """Merge key=value pairs into ~/.openclaw/.env (creates file if needed)."""
    target = openclaw_env_paths()[-1]
    _merge_env_file(target, keys)


def read_openclaw_env() -> dict[str, str]:
    """Read ~/.openclaw/.env (and OPENCLAW_STATE_DIR/.env when set)."""
    out: dict[str, str] = {}
    for env_path in openclaw_env_paths():
        if not env_path.exists():
            continue
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