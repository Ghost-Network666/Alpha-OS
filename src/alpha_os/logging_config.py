"""Alpha OS file logging — writes alpha-os.log in repo root."""

from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_CONFIGURED = False
_LOG_PATH: Path | None = None


def resolve_pkg_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (here.parent, here.parent.parent):
        if (candidate / "frontend").is_dir() or (candidate / "hermes_plugin").is_dir():
            return candidate
        if (candidate / "src" / "alpha_os").is_dir():
            return candidate.parent if candidate.name == "src" else candidate
    return here.parent.parent


def log_path(pkg_root: Path | None = None) -> Path:
    global _LOG_PATH
    if _LOG_PATH is not None:
        return _LOG_PATH
    root = pkg_root or resolve_pkg_root()
    env_path = __import__("os").environ.get("ALPHA_OS_LOG")
    _LOG_PATH = Path(env_path) if env_path else root / "alpha-os.log"
    return _LOG_PATH


def setup_logging(*, pkg_root: Path | None = None, level: int = logging.INFO) -> Path:
    """Configure console + root alpha-os.log file logging (idempotent)."""
    global _CONFIGURED
    path = log_path(pkg_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    if _CONFIGURED:
        return path

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(level)

    root = logging.getLogger("alpha_os")
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
    root.propagate = False

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvlog = logging.getLogger(name)
        uvlog.handlers.clear()
        uvlog.addHandler(file_handler)
        uvlog.addHandler(stream_handler)
        uvlog.setLevel(level)
        uvlog.propagate = False

    _CONFIGURED = True
    root.info("Alpha OS logging → %s", path)
    return path


def write_log_line(level: str, source: str, message: str, detail: Any = None) -> None:
    """Append a single line to alpha-os.log (for client/frontend events)."""
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"{ts} {level.upper()} [{source}] {message}"
    if detail is not None:
        line += f" | {detail}"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    logger = logging.getLogger("alpha_os.client")
    if level.lower() in ("error", "critical"):
        logger.error("%s — %s", message, detail or "")
    elif level.lower() == "warning":
        logger.warning("%s — %s", message, detail or "")
    else:
        logger.info("%s — %s", message, detail or "")


def log_exception(source: str, exc: BaseException) -> None:
    write_log_line("ERROR", source, str(exc), traceback.format_exc())