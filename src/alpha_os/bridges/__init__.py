"""Runtime bridges for Hermes and OpenClaw."""

from .detector import RuntimeInfo, detect_best, detect_hermes, detect_openclaw

__all__ = [
    "RuntimeInfo",
    "detect_best",
    "detect_hermes",
    "detect_openclaw",
]