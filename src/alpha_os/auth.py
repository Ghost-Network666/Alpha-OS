"""Optional API token auth for non-localhost deployments."""

from __future__ import annotations

import os
import secrets
from typing import Optional

from fastapi import Request, WebSocket


def api_token() -> Optional[str]:
    from alpha_os.config import inject_runtime_env

    inject_runtime_env()
    token = os.getenv("ALPHA_OS_API_TOKEN", "").strip()
    return token or None


def auth_enabled() -> bool:
    return api_token() is not None


def extract_token_from_request(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    header = request.headers.get("X-Alpha-OS-Token")
    if header:
        return header.strip() or None
    return None


def extract_token_from_websocket(ws: WebSocket) -> Optional[str]:
    token = ws.query_params.get("token")
    if token:
        return token.strip() or None
    return extract_token_from_request(ws)


def token_valid(provided: Optional[str]) -> bool:
    expected = api_token()
    if not expected:
        return True
    if not provided:
        return False
    return secrets.compare_digest(provided, expected)


PUBLIC_HTTP_PATHS = frozenset(
    {"/health", "/ready", "/api/bootstrap", "/docs", "/openapi.json", "/redoc"}
)


def requires_auth(path: str) -> bool:
    if not auth_enabled():
        return False
    if path in PUBLIC_HTTP_PATHS:
        return False
    return path.startswith("/api/")