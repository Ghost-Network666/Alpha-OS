"""Resolve Hermes / OpenClaw runtime paths from environment (install.sh, runtime.env)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

RuntimeChoice = Literal["hermes", "openclaw", "auto", "offline"]


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def hermes_root() -> Path:
    """~/.hermes root (parent of profiles/)."""
    raw = os.getenv("HERMES_HOME", "").strip()
    if not raw:
        return Path.home() / ".hermes"
    p = _expand(raw)
    if p.parent.name == "profiles" and p.parent.parent.name == ".hermes":
        return p.parent.parent
    return p


def hermes_profile_dir() -> Path | None:
    """Profile directory when HERMES_HOME points at ~/.hermes/profiles/<name>."""
    raw = os.getenv("HERMES_HOME", "").strip()
    if not raw:
        return None
    p = _expand(raw)
    if p.parent.name == "profiles":
        return p
    return None


def hermes_profile_name() -> str | None:
    """Profile name from HERMES_PROFILE or HERMES_HOME path."""
    prof = os.getenv("HERMES_PROFILE", "").strip()
    if prof:
        return prof
    profile_dir = hermes_profile_dir()
    if profile_dir is not None:
        return profile_dir.name
    return None


def openclaw_home() -> Path:
    raw = os.getenv("OPENCLAW_HOME", "").strip()
    if raw:
        return _expand(raw)
    return Path.home() / ".openclaw"


def active_runtime_choice() -> RuntimeChoice:
    """Runtime selected at install time or in ~/.alpha-os/config.yaml."""
    raw = os.getenv("ALPHA_OS_RUNTIME", "").strip().lower()
    if raw in ("hermes", "openclaw"):
        return raw  # type: ignore[return-value]
    return "auto"


def hermes_detected() -> bool:
    root = hermes_root()
    return root.is_dir() and (root / "profiles").is_dir()


def openclaw_detected() -> bool:
    return openclaw_home().is_dir()


def active_config_path() -> Path | None:
    """Primary config.yaml for the active runtime."""
    runtime = active_runtime_choice()
    if runtime == "openclaw" and openclaw_detected():
        for name in ("config.yaml", "config.yml"):
            path = openclaw_home() / name
            if path.is_file():
                return path
        return None
    if runtime in ("hermes", "auto") and hermes_detected():
        from alpha_os.config import hermes_config_path

        return hermes_config_path()
    if hermes_detected():
        from alpha_os.config import hermes_config_path

        return hermes_config_path()
    if openclaw_detected():
        for name in ("config.yaml", "config.yml"):
            path = openclaw_home() / name
            if path.is_file():
                return path
    return None


def runtime_summary() -> dict[str, str | None]:
    """Snapshot for logs and /api/config."""
    return {
        "runtime": active_runtime_choice(),
        "hermes_profile": hermes_profile_name(),
        "hermes_home": str(hermes_profile_dir() or hermes_root()),
        "hermes_root": str(hermes_root()),
        "openclaw_home": str(openclaw_home()),
        "config_path": str(active_config_path()) if active_config_path() else None,
    }