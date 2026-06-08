"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_api_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Most unit tests assume auth is disabled."""
    monkeypatch.delenv("ALPHA_OS_API_TOKEN", raising=False)