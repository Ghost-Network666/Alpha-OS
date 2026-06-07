"""Shared wake-word helpers and model path resolution."""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_WAKE_WORD = "hey alpha"
WAKE_THRESHOLD = 0.45

_MODEL_DIR = Path(__file__).resolve().parent / "models"
_HEY_ALPHA_MODEL = _MODEL_DIR / "hey_alpha_v0.1.onnx"


def hey_alpha_model_path() -> Path:
    return _HEY_ALPHA_MODEL


def hey_alpha_model_available() -> bool:
    return _HEY_ALPHA_MODEL.is_file()


def normalize_wake_word(wake_word: str) -> str:
    return (wake_word or DEFAULT_WAKE_WORD).strip().lower() or DEFAULT_WAKE_WORD


def strip_wake_word(transcript: str, wake_word: str = DEFAULT_WAKE_WORD) -> str:
    text = (transcript or "").strip()
    if not text:
        return ""

    wake = normalize_wake_word(wake_word)
    variants = {wake, "hey alfa", "hey alba"}
    lowered = text.lower()

    for phrase in variants:
        idx = lowered.find(phrase)
        if idx != -1:
            return text[idx + len(phrase) :].strip()

    return text


def contains_wake_word(transcript: str, wake_word: str = DEFAULT_WAKE_WORD) -> bool:
    lowered = (transcript or "").lower()
    wake = normalize_wake_word(wake_word)
    return any(v in lowered for v in (wake, "hey alfa", "hey alba"))


def wake_word_model_key(path: Path) -> str:
    stem = path.stem
    return re.sub(r"_v\d+(?:\.\d+)*$", "", stem)