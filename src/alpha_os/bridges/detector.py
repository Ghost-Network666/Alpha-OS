"""Auto-detect Hermes Agent and OpenClaw runtimes on the local machine."""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from alpha_os.config import (
    active_hermes_profile,
    hermes_home,
    read_hermes_config,
    read_hermes_env,
    read_openclaw_config,
    read_openclaw_env,
)
from alpha_os.runtime_env import openclaw_home

logger = logging.getLogger("alpha_os.detector")

HERMES_HOME = hermes_home()
OPENCLAW_HOME = openclaw_home()


def hermes_installed() -> bool:
    if hermes_home().exists():
        return True
    return _hermes_likely_running()


def openclaw_installed() -> bool:
    return openclaw_home().exists()


def _hermes_likely_running() -> bool:
    """Detect if Hermes gateway or API is connected/running on a live port or process.
    This supports 'anything connected to .hermes gateway' or 'been used on a live port for .hermes'.
    """
    # 1. Process check (hermes or hermes-agent running)
    try:
        out = subprocess.check_output(
            ["pgrep", "-f", r"hermes|hermes-agent"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        if out.strip():
            return True
    except Exception:
        pass

    # 2. Listening ports check - only if the line mentions hermes or we have config evidence
    common_hermes_ports = {8642, 9999, 8081, 9000}
    try:
        out = subprocess.check_output(
            ["ss", "-tlnp"], text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            line_l = line.lower()
            if "hermes" in line_l:
                return True
            m = re.search(r":(\d+)", line)
            if m:
                p = int(m.group(1))
                if p in common_hermes_ports and "hermes" in line_l:
                    return True
    except Exception:
        pass

    # 3. Fallback: check if any Hermes config/env references a port that is currently listening
    try:
        env = read_hermes_env()
        for key in ("API_SERVER_PORT", "HERMES_GATEWAY_URL"):
            val = env.get(key, "")
            m = re.search(r":(\d+)", val)
            if m:
                p = int(m.group(1))
                # quick check if that port is listening
                try:
                    out2 = subprocess.check_output(
                        ["ss", "-tlnp"], text=True, stderr=subprocess.DEVNULL
                    )
                    if f":{p}" in out2:
                        return True
                except Exception:
                    pass
    except Exception:
        pass

    return False


PALETTE = ["#00f0ff", "#39ff14", "#ff2a6d", "#ff9f1c", "#7b2cbf"]


@dataclass
class RuntimeInfo:
    name: str  # "hermes" | "openclaw" | "offline"
    connected: bool = False
    gateway_url: str = ""
    api_key: str = ""
    ws_url: str = ""
    details: dict[str, Any] = field(default_factory=dict)


async def _probe_http(url: str, headers: Optional[dict] = None, timeout: float = 3.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for path in ("/health", "/v1/health", "/v1/capabilities", "/"):
                try:
                    r = await client.get(f"{url.rstrip('/')}{path}", headers=headers or {})
                    if r.status_code == 200:
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


def _env_gateway_url(env: dict[str, str]) -> str | None:
    if env.get("HERMES_GATEWAY_URL"):
        return env["HERMES_GATEWAY_URL"]
    host = env.get("API_SERVER_HOST")
    port = env.get("API_SERVER_PORT")
    if host and port:
        scheme = "https" if str(port) == "443" else "http"
        return f"{scheme}://{host}:{port}"
    return None


def _hermes_profile_envs() -> list[dict[str, str]]:
    """Global + every profile .env under ~/.hermes/profiles/*/."""
    import os
    from pathlib import Path

    out: list[dict[str, str]] = []
    seen_paths: set[str] = set()

    def _parse_env(path: Path) -> dict[str, str]:
        parsed: dict[str, str] = {}
        if not path.exists():
            return parsed
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                parsed[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
        return parsed

    global_env = hermes_home() / ".env"
    if str(global_env) not in seen_paths:
        seen_paths.add(str(global_env))
        out.append(_parse_env(global_env))

    profiles_root = hermes_home() / "profiles"
    if profiles_root.is_dir():
        for profile_dir in sorted(profiles_root.iterdir()):
            env_path = profile_dir / ".env"
            if env_path.is_file() and str(env_path) not in seen_paths:
                seen_paths.add(str(env_path))
                out.append(_parse_env(env_path))

    active = active_hermes_profile()
    if active:
        os.environ.setdefault("HERMES_PROFILE", active)
    return out


def _hermes_candidates() -> list[str]:
    urls: list[str] = []
    for env in _hermes_profile_envs():
        url = _env_gateway_url(env)
        if url:
            urls.append(url)

    env = read_hermes_env()
    url = _env_gateway_url(env)
    if url:
        urls.append(url)

    cfg = read_hermes_config()
    api = cfg.get("api_server") if isinstance(cfg.get("api_server"), dict) else {}
    if api.get("host") and api.get("port"):
        urls.append(f"http://{api['host']}:{api['port']}")

    # Include any live ports we discovered (for "live port for .hermes" cases)
    try:
        live_ports = []
        out = subprocess.check_output(
            ["ss", "-tlnp"], text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if "hermes" in line.lower():
                m = re.search(r":(\d+)", line)
                if m:
                    live_ports.append(int(m.group(1)))
            else:
                m = re.search(r":(\d+)", line)
                if m and int(m.group(1)) in (8642, 9999, 8080, 8081, 9000):
                    live_ports.append(int(m.group(1)))
        for p in sorted(set(live_ports)):
            urls.append(f"http://127.0.0.1:{p}")
            urls.append(f"http://localhost:{p}")
    except Exception:
        pass

    urls.extend([
        "http://127.0.0.1:9999",
        "http://localhost:9999",
        "http://127.0.0.1:8642",
        "http://localhost:8642",
    ])
    seen: set[str] = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _openclaw_candidates() -> list[str]:
    cfg = read_openclaw_config()
    gw = cfg.get("gateway", {}) if isinstance(cfg.get("gateway"), dict) else {}
    port = gw.get("port", 18789)
    urls: list[str] = []

    env = read_openclaw_env()
    for key in ("OPENCLAW_GATEWAY_URL", "GATEWAY_URL"):
        if env.get(key):
            urls.append(env[key])

    if gw.get("url"):
        urls.append(str(gw["url"]))
    if gw.get("bind") and port:
        bind = str(gw["bind"])
        if bind.startswith(":"):
            bind = f"127.0.0.1{bind}"
        urls.append(f"http://{bind}")
        urls.append(f"ws://{bind}")

    urls.extend([
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
        f"ws://127.0.0.1:{port}",
        f"ws://localhost:{port}",
    ])
    seen: set[str] = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _hermes_api_key() -> str:
    env = read_hermes_env()
    return (
        env.get("API_SERVER_KEY")
        or env.get("HERMES_API_KEY")
        or ""
    )


def _openclaw_token() -> str:
    import os

    token = os.getenv("OPENCLAW_GATEWAY_TOKEN", "") or os.getenv("OPENCLAW_TOKEN", "")
    if token:
        return token
    env = read_openclaw_env()
    token = env.get("OPENCLAW_GATEWAY_TOKEN") or env.get("OPENCLAW_TOKEN") or env.get("GATEWAY_TOKEN", "")
    if token:
        return token
    cfg = read_openclaw_config()
    gw = cfg.get("gateway", {}) if isinstance(cfg.get("gateway"), dict) else {}
    auth = gw.get("auth", {}) if isinstance(gw.get("auth"), dict) else {}
    return str(auth.get("token", "") or "")


async def detect_hermes() -> RuntimeInfo:
    info = RuntimeInfo(name="hermes")
    home_exists = hermes_home().exists()
    running = _hermes_likely_running()

    if not home_exists and not running:
        info.details["reason"] = "no ~/.hermes directory and no live Hermes process or port detected"
        return info

    api_key = _hermes_api_key()
    info.api_key = api_key
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    for url in _hermes_candidates():
        http_url = url.replace("ws://", "http://").replace("wss://", "https://")
        if await _probe_http(http_url, headers=headers):
            info.connected = True
            info.gateway_url = http_url
            info.details["home"] = str(hermes_home())
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(
                        f"{http_url}/v1/capabilities",
                        headers=headers,
                    )
                    if r.status_code == 200:
                        info.details["capabilities"] = r.json()
            except Exception:
                pass
            return info

    info.gateway_url = _hermes_candidates()[0] if _hermes_candidates() else "http://127.0.0.1:9999"
    info.details["reason"] = "hermes home found but API server not reachable"
    return info


async def detect_openclaw() -> RuntimeInfo:
    info = RuntimeInfo(name="openclaw")
    if not openclaw_home().exists():
        info.details["reason"] = "no ~/.openclaw directory"
        return info

    token = _openclaw_token()
    info.api_key = token

    for url in _openclaw_candidates():
        http_url = url.replace("ws://", "http://").replace("wss://", "https://")
        if await _probe_http(http_url):
            info.connected = True
            info.gateway_url = http_url
            info.ws_url = http_url.replace("http://", "ws://").replace("https://", "wss://")
            info.details["home"] = str(openclaw_home())
            return info

    port = 18789
    cfg = read_openclaw_config()
    gw = cfg.get("gateway", {}) if isinstance(cfg.get("gateway"), dict) else {}
    port = gw.get("port", port)
    info.gateway_url = f"http://127.0.0.1:{port}"
    info.ws_url = f"ws://127.0.0.1:{port}"
    info.details["reason"] = "openclaw home found but gateway not reachable"
    return info


async def detect_best() -> RuntimeInfo:
    """Prefer connected Hermes, then connected OpenClaw, else offline with best guess."""
    hermes, openclaw = await asyncio.gather(detect_hermes(), detect_openclaw())
    if hermes.connected:
        return hermes
    if openclaw.connected:
        return openclaw
    if hermes_home().exists():
        return hermes
    if openclaw_home().exists():
        return openclaw
    return RuntimeInfo(name="offline", details={"reason": "no runtime detected"})


def color_for_index(i: int) -> str:
    return PALETTE[i % len(PALETTE)]