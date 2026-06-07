"""Hot-reload Hermes gateway after ~/.hermes/config.yaml changes."""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from typing import Any, Optional

import httpx

from alpha_os.config import read_hermes_env

logger = logging.getLogger("alpha_os.voice")

RELOAD_HTTP_PATHS: tuple[tuple[str, str], ...] = (
    ("POST", "/v1/reload"),
    ("POST", "/api/reload"),
    ("POST", "/api/config/reload"),
    ("POST", "/reload"),
    ("GET", "/v1/reload-config"),
    ("POST", "/v1/reload-config"),
)

CLI_RELOAD_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("hermes", "gateway", "reload-config"),
    ("hermes", "gateway", "reload"),
    ("hermes", "config", "reload"),
)


def _hermes_api_key() -> str:
    env = read_hermes_env()
    return env.get("API_SERVER_KEY") or env.get("HERMES_API_KEY") or ""


def _headers(api_key: str) -> dict[str, str]:
    h = {"Accept": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


async def _probe_reload_http(
    gateway_url: str,
    *,
    api_key: str = "",
    timeout: float = 4.0,
) -> Optional[dict[str, Any]]:
    base = gateway_url.rstrip("/")
    headers = _headers(api_key)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for method, path in RELOAD_HTTP_PATHS:
            url = f"{base}{path}"
            try:
                if method == "POST":
                    r = await client.post(url, headers=headers, json={})
                else:
                    r = await client.get(url, headers=headers)
                if r.status_code in (200, 202, 204):
                    detail: Any = None
                    if r.content:
                        try:
                            detail = r.json()
                        except Exception:
                            detail = r.text[:200]
                    return {
                        "ok": True,
                        "method": "http",
                        "path": path,
                        "status": r.status_code,
                        "detail": detail,
                    }
            except Exception:
                continue
    return None


def _probe_reload_cli() -> Optional[dict[str, Any]]:
    if not shutil.which("hermes"):
        return None
    for cmd in CLI_RELOAD_COMMANDS:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            if proc.returncode == 0:
                return {
                    "ok": True,
                    "method": "cli",
                    "command": " ".join(cmd),
                    "detail": (proc.stdout or proc.stderr or "").strip()[:200],
                }
        except Exception:
            continue
    return None


async def reload_hermes_gateway(
    gateway_url: Optional[str] = None,
    *,
    hermes_connected: bool = False,
) -> dict[str, Any]:
    """Ask Hermes gateway to reload config after yaml save."""
    url = (gateway_url or "").strip()
    api_key = _hermes_api_key()

    if url:
        http_result = await _probe_reload_http(url, api_key=api_key)
        if http_result:
            return http_result

    if hermes_connected and url:
        return {
            "ok": False,
            "method": "http",
            "detail": "Gateway reachable but no reload endpoint responded",
            "hint": "Restart `hermes gateway` to pick up config.yaml changes",
        }

    loop = asyncio.get_event_loop()
    cli_result = await loop.run_in_executor(None, _probe_reload_cli)
    if cli_result:
        return cli_result

    return {
        "ok": False,
        "method": "none",
        "detail": "Hermes gateway offline or reload API unavailable",
        "hint": "Config saved to ~/.hermes/config.yaml — restart gateway if needed",
    }