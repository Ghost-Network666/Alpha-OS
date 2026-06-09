"""Alpha OS FastAPI server."""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from alpha_os.install_config import _tailscale_dns_name
from alpha_os.logging_config import log_exception, log_path, setup_logging, write_log_line
from alpha_os.bridges.hermes_bridge import HermesBridge
from alpha_os.bridges.openclaw_bridge import OpenClawBridge
from alpha_os.bridges.detector import color_for_index, detect_best
from alpha_os.config import get, load_config, set_hermes_env, set_key
from alpha_os.voice.hermes_sync import apply_voice_config, load_voice_config
from alpha_os.core.alpha import Alpha
from alpha_os.core.events import (
    LiveEventBuffer,
    ProfileActivityTracker,
    human_activity_text,
)
from alpha_os.integrations.mcp_bridge import MCPRegistry
from alpha_os.integrations.tailscale import TailscaleStatus

setup_logging()
logger = logging.getLogger("alpha_os.server")

STATIC_DIR = Path(__file__).parent / "dashboard" / "static"
from alpha_os.config import hermes_home
from alpha_os.runtime_env import openclaw_home, runtime_summary

ALPHA = Alpha()


def _hermes_installed() -> bool:
    return hermes_home().exists()


def _is_live() -> bool:
    """Dashboard active when Hermes or OpenClaw home exists (UI stays up if gateway drops)."""
    return _hermes_installed() or openclaw_home().exists()


def _gateway_online() -> bool:
    if _active_runtime == "hermes":
        return HERMES_BRIDGE._connected
    if _active_runtime == "openclaw":
        return OPENCLAW_BRIDGE._connected
    return False


def _empty_panel_state() -> dict[str, Any]:
    return {
        "agents": [],
        "greeting": "",
        "memory": {"recent": [], "history_length": 0},
        "integrations": {
            "connected": False,
            "runtime": "offline",
            "toolsets": [],
            "skills": [],
            "sessions": [],
        },
        "metrics": {
            "sessions": 0,
            "agents": 0,
            "tools": 0,
            "toolsets": 0,
            "skills": 0,
            "plugins": 0,
            "events_per_min": 0,
        },
        "capabilities": [],
        "gateway_online": False,
        "live_events": [],
        "event_seq": 0,
        "orb_pulse": False,
        "mcp": {
            "connected": False,
            "server_count": 0,
            "tool_count": 0,
            "servers": [],
        },
        "tailscale": {
            "available": False,
            "backend_state": "offline",
            "connected": False,
            "self_ip": None,
            "hostname": None,
            "dns_name": None,
            "exit_node": None,
            "peers": [],
            "uptime_sec": 0.0,
            "downtime_sec": 0.0,
        },
        "polymarket": {
            "connected": False,
            "pnl_today": None,
            "open_positions": None,
            "win_rate": None,
        },
    }
HERMES_BRIDGE = HermesBridge()
OPENCLAW_BRIDGE = OpenClawBridge()
TAILSCALE = TailscaleStatus()
MCP_REGISTRY = MCPRegistry()
LIVE_EVENTS = LiveEventBuffer()
PROFILE_ACTIVITY = ProfileActivityTracker()
_last_hermes_retry = 0.0
_last_oc_retry = 0.0
_active_runtime = "offline"
_stream_tasks: list[asyncio.Task] = []
_voice_loop: Any = None


def _apply_config_to_bridges() -> None:
    cfg = load_config()
    runtime = cfg.get("runtime", "auto")
    if runtime == "hermes" or (runtime == "auto" and cfg.get("hermes", {}).get("gateway_url")):
        h = cfg.get("hermes", {})
        if h.get("gateway_url"):
            HERMES_BRIDGE.gateway_url = h["gateway_url"].rstrip("/")
        if h.get("api_key"):
            HERMES_BRIDGE.api_key = h["api_key"]
    if runtime == "openclaw" or (runtime == "auto" and cfg.get("openclaw", {}).get("ws_url")):
        o = cfg.get("openclaw", {})
        if o.get("ws_url"):
            OPENCLAW_BRIDGE.ws_url = o["ws_url"]
        if o.get("token"):
            OPENCLAW_BRIDGE.token = o["token"]


async def _init_bridges() -> None:
    global _active_runtime
    _apply_config_to_bridges()
    HERMES_BRIDGE._resolve_api_key()
    info = await detect_best()
    if info.name == "hermes" and info.gateway_url:
        HERMES_BRIDGE.gateway_url = info.gateway_url
        if info.api_key:
            HERMES_BRIDGE.api_key = info.api_key
        else:
            HERMES_BRIDGE._resolve_api_key()
    if info.name == "openclaw":
        if info.ws_url:
            OPENCLAW_BRIDGE.ws_url = info.ws_url
        if info.api_key:
            OPENCLAW_BRIDGE.token = info.api_key

    if info.name == "hermes":
        ok = await HERMES_BRIDGE.connect()
        _active_runtime = "hermes" if ok else "offline"
        logger.info("Hermes gateway %s", "connected" if ok else "offline")
    elif info.name == "openclaw":
        ok = await OPENCLAW_BRIDGE.connect()
        _active_runtime = "openclaw" if ok else "offline"
        logger.info("OpenClaw gateway %s", "connected" if ok else "offline")
    else:
        _active_runtime = "offline"
        logger.info("No runtime detected — panels will start empty")


def _polymarket_metrics(mcp_data: dict[str, Any]) -> dict[str, Any]:
    """Surface Polymarket MCP when connected — values filled when tools respond."""
    servers = mcp_data.get("servers") or []
    poly = next(
        (
            s
            for s in servers
            if isinstance(s, dict)
            and "polymarket" in str(s.get("name", "")).lower()
            and s.get("connected")
        ),
        None,
    )
    if not poly:
        return {
            "connected": False,
            "pnl_today": None,
            "open_positions": None,
            "win_rate": None,
        }
    return {
        "connected": True,
        "server": poly.get("name"),
        "tool_count": poly.get("tool_count", 0),
        "pnl_today": None,
        "open_positions": None,
        "win_rate": None,
    }


def _build_integrations() -> dict[str, Any]:
    if _active_runtime == "hermes" and HERMES_BRIDGE._connected:
        return {
            "connected": True,
            "runtime": "hermes",
            "toolsets": HERMES_BRIDGE.get_toolsets(),
            "skills": HERMES_BRIDGE.get_skills(),
            "sessions": HERMES_BRIDGE.get_sessions(),
            "error": None,
        }
    if _active_runtime == "openclaw" and OPENCLAW_BRIDGE._connected:
        return OPENCLAW_BRIDGE.get_integrations()
    return {
        "connected": False,
        "runtime": _active_runtime,
        "toolsets": [],
        "skills": [],
        "sessions": [],
        "error": "Gateway offline",
    }


def _build_profile_agents(
    *,
    gateway_online: bool,
    active_runtime: str,
) -> list[dict[str, Any]]:
    """Hermes profile agents for the dashboard row (alpha, rewards, trader, …)."""
    from alpha_os.config import (
        active_hermes_profile,
        list_hermes_profiles,
        read_hermes_profile_config,
    )

    if not _hermes_installed():
        return []

    active = active_hermes_profile()
    cards: list[dict[str, Any]] = []
    for i, name in enumerate(list_hermes_profiles()):
        cfg = read_hermes_profile_config(name)
        model = cfg.get("model") if isinstance(cfg.get("model"), dict) else {}
        model_default = str(model.get("default") or "").strip() or None
        model_provider = str(model.get("provider") or "").strip() or None
        is_active = name == active
        if is_active and gateway_online and active_runtime == "hermes":
            status = "LIVE"
        elif is_active:
            status = "ACTIVE"
        else:
            status = "STANDBY"
        title_parts = [p for p in (model_default, model_provider) if p]
        activity_entry = PROFILE_ACTIVITY.get(name)
        if (
            not activity_entry
            and is_active
            and gateway_online
            and active_runtime == "hermes"
        ):
            last = HERMES_BRIDGE._last_event
            if last:
                activity_entry = {
                    "text": human_activity_text("hermes", last),
                    "ts": time.time(),
                    "busy": str(
                        last.get("status") or last.get("state") or ""
                    ).lower()
                    in ("running", "in_progress", "active", "started"),
                }
        activity = None
        busy = False
        if activity_entry:
            activity = str(activity_entry.get("text") or "").strip() or None
            busy = bool(activity_entry.get("busy"))
            if busy and is_active and gateway_online:
                status = "LIVE"

        cards.append(
            {
                "id": f"profile-{name}",
                "kind": "profile",
                "name": name,
                "title": " · ".join(title_parts) if title_parts else "Hermes profile",
                "model": model_default,
                "provider": model_provider,
                "status": status,
                "active": is_active,
                "color": color_for_index(i),
                "activity": activity,
                "busy": busy,
            }
        )
    return cards


async def _build_state() -> dict[str, Any]:
    global _last_hermes_retry, _last_oc_retry, _active_runtime
    now = time.time()

    if _active_runtime == "hermes":
        if not HERMES_BRIDGE._connected and now - _last_hermes_retry > 8:
            _last_hermes_retry = now
            await HERMES_BRIDGE.connect()
    elif _active_runtime == "openclaw":
        if not OPENCLAW_BRIDGE._connected and now - _last_oc_retry > 8:
            _last_oc_retry = now
            await OPENCLAW_BRIDGE.connect()

    hermes_installed = _hermes_installed()
    hermes_connected = HERMES_BRIDGE._connected
    openclaw_connected = OPENCLAW_BRIDGE._connected
    gateway_online = _gateway_online()
    live = _is_live()

    capabilities: list[dict] = []
    if _active_runtime == "hermes":
        capabilities = HERMES_BRIDGE.get_capabilities() or []
    elif _active_runtime == "openclaw" and openclaw_connected:
        capabilities = OPENCLAW_BRIDGE.get_agent_list() or []

    data = ALPHA.get_dashboard_state(
        hermes_agents=capabilities if gateway_online else None,
        runtime=_active_runtime,
    )
    data["hermes"] = HERMES_BRIDGE.get_status()
    data["openclaw"] = OPENCLAW_BRIDGE.get_status()
    data["hermes_installed"] = hermes_installed
    data["hermes_connected"] = hermes_connected
    data["openclaw_connected"] = openclaw_connected
    data["gateway_online"] = gateway_online
    data["live"] = live
    data["capabilities"] = capabilities
    data["agents"] = capabilities  # legacy alias

    if not live:
        data.update(_empty_panel_state())
        data["capabilities"] = []
        data["agents"] = []
        data["profile_agents"] = []
    else:
        integrations = _build_integrations()
        if not gateway_online:
            integrations = {
                **integrations,
                "connected": False,
                "error": (
                    "Hermes gateway offline"
                    if _active_runtime == "hermes"
                    else "OpenClaw gateway offline"
                    if _active_runtime == "openclaw"
                    else "Gateway offline"
                ),
            }
        data["integrations"] = integrations
        toolsets = integrations.get("toolsets", [])
        skills = integrations.get("skills", [])
        sessions = integrations.get("sessions", [])
        mcp_data = MCP_REGISTRY.get_panel_data()
        tool_count = sum(
            len(ts.get("tools", [])) if isinstance(ts, dict) else 0 for ts in toolsets
        )
        if not tool_count and mcp_data.get("tool_count"):
            tool_count = int(mcp_data["tool_count"])
        cap_toolsets = sum(1 for c in capabilities if c.get("kind") == "toolset")
        cap_skills = sum(1 for c in capabilities if c.get("kind") == "skill")

        profile_agents = _build_profile_agents(
            gateway_online=gateway_online,
            active_runtime=_active_runtime,
        )
        data["profile_agents"] = profile_agents

        data["metrics"] = {
            "sessions": len(sessions),
            "agents": len(profile_agents),
            "toolsets": cap_toolsets or len(toolsets),
            "skills": cap_skills or len(skills),
            "tools": tool_count,
            "plugins": len(mcp_data.get("servers") or []),
            "events_per_min": LIVE_EVENTS.events_per_minute() if gateway_online else 0,
        }
        data["polymarket"] = _polymarket_metrics(mcp_data)
        data["live_events"] = LIVE_EVENTS.get_recent(20)
        data["event_seq"] = LIVE_EVENTS.latest_seq()
        data["orb_pulse"] = LIVE_EVENTS.consume_pulse() if gateway_online else False
        data["mcp"] = mcp_data
        data["memory"] = ALPHA.memory.to_summary()
    try:
        from alpha_os.voice import get_voice_providers
        voice_providers = get_voice_providers(
            hermes_connected=HERMES_BRIDGE._connected,
            openclaw_connected=OPENCLAW_BRIDGE._connected,
            runtime=_active_runtime,
        )
    except Exception:
        voice_providers = []
    voice_cfg = load_voice_config()
    data["voice_config"] = {
        **voice_cfg,
        "enabled": bool(voice_cfg.get("server_wake", False)),
        "browser_mic": bool(voice_cfg.get("browser_wake", True)),
        "providers": voice_providers,
    }
    try:
        from alpha_os.voice.live import build_voice_live

        data["voice_live"] = build_voice_live()
    except Exception:
        data["voice_live"] = None
    ts_dns = _tailscale_dns_name()
    data["log_path"] = str(log_path())
    data["tailscale_https_url"] = f"https://{ts_dns}" if ts_dns else None
    data["tailscale"] = TAILSCALE.to_dict()
    return data


def _on_gateway_event(source: str, event: dict[str, Any]) -> None:
    LIVE_EVENTS.push(source, event)
    try:
        from alpha_os.config import active_hermes_profile

        PROFILE_ACTIVITY.record_event(
            source,
            event,
            fallback_profile=active_hermes_profile(),
        )
    except Exception:
        pass
    summary = LIVE_EVENTS.get_recent(1)
    if summary and _is_live():
        ALPHA.memory.add_turn("gateway", f"[{source}] {summary[0]['summary']}")
    if _active_runtime == "openclaw" and source == "openclaw":
        asyncio.create_task(_refresh_openclaw_on_event())


async def _refresh_openclaw_on_event() -> None:
    try:
        await OPENCLAW_BRIDGE._refresh_state()
    except Exception:
        pass


async def _mcp_refresh_loop() -> None:
    while True:
        try:
            await MCP_REGISTRY.refresh(sample_data=True)
        except Exception:
            pass
        await asyncio.sleep(60)


async def _hermes_event_stream() -> None:
    while True:
        if _active_runtime != "hermes" or not HERMES_BRIDGE._connected:
            await asyncio.sleep(5)
            continue
        await HERMES_BRIDGE.stream_events(lambda e: _on_gateway_event("hermes", e))
        await asyncio.sleep(5)


def _start_event_streams() -> None:
    OPENCLAW_BRIDGE.on_event(lambda e: _on_gateway_event("openclaw", e))
    _stream_tasks.append(asyncio.create_task(_hermes_event_stream()))


async def _stop_voice_loop() -> None:
    global _voice_loop
    if _voice_loop:
        try:
            await _voice_loop.stop()
        except Exception:
            pass
        _voice_loop = None


async def _start_voice_loop() -> None:
    global _voice_loop
    voice_cfg = load_voice_config()
    if not voice_cfg.get("server_wake", False):
        return
    try:
        from alpha_os.voice import VoiceLoop

        async def on_transcript(text: str) -> None:
            reply = ALPHA.process(text)
            LIVE_EVENTS.push("voice", {"type": "transcript", "text": text, "reply": reply})

        _voice_loop = VoiceLoop(
            wake_word=str(voice_cfg.get("wake_word", "hey alpha")),
            on_transcript=on_transcript,
        )
        await _voice_loop.start()
    except Exception as e:
        logger.warning("Voice loop unavailable: %s", e)


async def _restart_voice_loop() -> None:
    await _stop_voice_loop()
    await _start_voice_loop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from alpha_os.runtime_sync import sync_runtime_config

    summary = runtime_summary()
    logger.info(
        "Alpha OS server starting — runtime=%s profile=%s config=%s log=%s",
        summary.get("runtime"),
        summary.get("hermes_profile"),
        summary.get("config_path"),
        log_path(),
    )
    await sync_runtime_config(sync_voice=True, only_missing=False)
    await _init_bridges()
    _start_event_streams()
    try:
        await TAILSCALE.refresh()
    except Exception:
        pass
    asyncio.create_task(_tailscale_loop())
    asyncio.create_task(_mcp_refresh_loop())
    await MCP_REGISTRY.refresh(sample_data=True)
    await _start_voice_loop()
    yield
    for task in _stream_tasks:
        task.cancel()
    await _stop_voice_loop()
    await HERMES_BRIDGE.disconnect()
    await OPENCLAW_BRIDGE.disconnect()
    if hasattr(ALPHA.memory, "close"):
        ALPHA.memory.close()


async def _tailscale_loop():
    while True:
        try:
            ts = await TAILSCALE.refresh()
            ALPHA.memory.update_tailscale(**{k: v for k, v in ts.items() if v is not None})
        except Exception:
            pass
        await asyncio.sleep(5)


app = FastAPI(title="Alpha OS", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def api_auth_middleware(request: Request, call_next):
    from alpha_os.auth import (
        extract_token_from_request,
        requires_auth,
        token_valid,
    )

    if requires_auth(request.url.path):
        if not token_valid(extract_token_from_request(request)):
            return JSONResponse(
                status_code=401,
                content={"ok": False, "error": "Unauthorized"},
            )
    return await call_next(request)


@app.middleware("http")
async def log_unhandled_errors(request: Request, call_next):
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            write_log_line(
                "ERROR",
                "http",
                f"{request.method} {request.url.path} → {response.status_code}",
            )
        return response
    except Exception as exc:
        log_exception("http", exc)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(exc), "log": str(log_path())},
        )


class ClientLogRequest(BaseModel):
    level: str = "info"
    source: str = "frontend"
    message: str
    detail: Optional[str] = None


@app.post("/api/log")
async def api_client_log(req: ClientLogRequest):
    write_log_line(req.level, req.source, req.message, req.detail)
    return {"ok": True, "log": str(log_path())}


@app.get("/api/log/path")
async def api_log_path():
    return {"path": str(log_path())}


def _cors_origins() -> list[str]:
    origins = {
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:4000",
        "http://localhost:4000",
    }
    fe_port = int(get("frontend.port", 3000))
    for host in ("127.0.0.1", "localhost"):
        origins.add(f"http://{host}:{fe_port}")
    ts_ip = None
    try:
        import shutil
        import subprocess

        if shutil.which("tailscale"):
            proc = subprocess.run(
                ["tailscale", "ip", "-4"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if proc.returncode == 0:
                ts_ip = (proc.stdout or "").strip().splitlines()[0].strip()
    except Exception:
        ts_ip = None
    if ts_ip:
        origins.add(f"http://{ts_ip}:{fe_port}")
        origins.add(f"https://{ts_ip}:{fe_port}")
    try:
        import json
        import subprocess

        if shutil.which("tailscale"):
            proc = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if proc.returncode == 0:
                dns = (json.loads(proc.stdout).get("Self") or {}).get("DNSName", "")
                dns = dns.rstrip(".") if isinstance(dns, str) else ""
                if dns:
                    origins.add(f"https://{dns}")
    except Exception:
        pass
    return sorted(origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def embed_headers(request, call_next):
    response = await call_next(request)
    if request.url.path in ("/", "/static/index.html", "/api/state"):
        response.headers["Access-Control-Allow-Origin"] = "*"
    if request.url.path in ("/", "/static/index.html"):
        response.headers["Content-Security-Policy"] = "frame-ancestors *"
        if "x-frame-options" in response.headers:
            del response.headers["x-frame-options"]
    return response


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class CommandRequest(BaseModel):
    command: str


class ConfigRequest(BaseModel):
    runtime: Optional[str] = None
    hermes_gateway_url: Optional[str] = None
    hermes_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    openclaw_ws_url: Optional[str] = None
    openclaw_token: Optional[str] = None


class VoiceConfigRequest(BaseModel):
    wake_word: Optional[str] = None
    browser_wake: Optional[bool] = None
    server_wake: Optional[bool] = None
    enabled: Optional[bool] = None  # alias for server_wake
    grok_oauth: Optional[bool] = None
    hermes_profile: Optional[str] = None
    model_provider: Optional[str] = None
    model_default: Optional[str] = None
    record_key: Optional[str] = None
    max_recording_seconds: Optional[int] = None
    auto_tts: Optional[bool] = None
    beep_enabled: Optional[bool] = None
    silence_threshold: Optional[int] = None
    silence_duration: Optional[float] = None
    stt_enabled: Optional[bool] = None
    stt_provider: Optional[str] = None
    stt_model: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_model: Optional[str] = None
    provider_id: Optional[str] = None
    provider_enabled: Optional[bool] = None


class TtsRequest(BaseModel):
    text: str
    provider: Optional[str] = None
    voice: Optional[str] = None


class ProfileSwitchRequest(BaseModel):
    profile: str


class ProfileAgentRequest(BaseModel):
    model_provider: Optional[str] = None
    model_default: Optional[str] = None
    disabled_toolsets: Optional[list[str]] = None
    mcp_enabled: Optional[dict[str, bool]] = None


class VoiceUsageReport(BaseModel):
    kind: str  # "tts" | "stt"
    provider: Optional[str] = None
    characters: int = 0


@app.get("/health")
async def health():
    from alpha_os import __version__

    return {"ok": True, "service": "alpha-os", "version": __version__}


@app.get("/ready")
async def ready():
    from alpha_os.auth import auth_enabled

    return {
        "ok": True,
        "runtime": _active_runtime,
        "auth": auth_enabled(),
        "mcp_servers": MCP_REGISTRY.get_panel_data().get("server_count", 0),
    }


@app.get("/api/bootstrap")
async def api_bootstrap():
    """Frontend connection info — env from ~/.hermes/.env and ~/.openclaw/.env."""
    import os

    from alpha_os.auth import api_token as _api_token
    from alpha_os.config import alpha_os_host, alpha_os_port, inject_runtime_env, runtime_env_sources

    inject_runtime_env(_active_runtime)
    host = alpha_os_host()
    port = alpha_os_port()
    token = _api_token()
    ws_url = f"ws://{host}:{port}/ws/state"
    if token:
        ws_url = f"{ws_url}?token={token}"
    return {
        "ok": True,
        "api_url": f"http://{host}:{port}",
        "ws_url": ws_url,
        "auth_required": bool(token),
        "runtime": _active_runtime,
        "env_sources": runtime_env_sources(_active_runtime),
        "frontend_port": int(os.getenv("ALPHA_OS_FRONTEND_PORT", "4000")),
    }


@app.get("/")
async def index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Alpha OS — dashboard static files not found"}


@app.get("/api/state")
async def api_state():
    return await _build_state()


@app.post("/api/command")
async def api_command(req: CommandRequest):
    cmd = (req.command or "").strip()
    if not cmd:
        return {"reply": "At your service, sir.", "ok": True, "relayed": False}

    if _is_live():
        ALPHA.memory.add_turn("user", cmd)
    relayed: dict[str, Any] | None = None
    if _active_runtime == "hermes" and HERMES_BRIDGE._connected:
        relayed = await HERMES_BRIDGE.send_command(cmd)
    elif _active_runtime == "openclaw" and OPENCLAW_BRIDGE._connected:
        relayed = await OPENCLAW_BRIDGE.send_command(cmd)

    if relayed and relayed.get("reply"):
        reply = str(relayed["reply"])
        ok = bool(relayed.get("ok", True))
    elif relayed and relayed.get("error"):
        reply = (
            f"Gateway relay failed ({relayed['error']}). "
            + ALPHA.generate_reply(cmd)
        )
        ok = False
    else:
        reply = ALPHA.generate_reply(cmd)
        ok = True

    if _is_live():
        ALPHA.memory.add_turn("alpha", reply)
        cmd_event = {"type": "command", "text": cmd, "reply": reply[:120]}
        LIVE_EVENTS.push("command", cmd_event)
        try:
            from alpha_os.config import active_hermes_profile

            PROFILE_ACTIVITY.record_event(
                "command",
                cmd_event,
                fallback_profile=active_hermes_profile(),
            )
        except Exception:
            pass
    return {
        "reply": reply,
        "ok": ok,
        "relayed": bool(relayed and relayed.get("ok")),
    }


@app.get("/api/greet")
async def api_greet():
    return {"greeting": ALPHA.get_dashboard_state()["greeting"]}


def _voice_request_payload(req: VoiceConfigRequest) -> dict[str, Any]:
    data = req.model_dump(exclude_none=True)
    if req.enabled is not None and "server_wake" not in data:
        data["server_wake"] = req.enabled
    return data


@app.get("/api/voice/config")
async def voice_config_get():
    from alpha_os.voice import get_voice_providers

    voice_cfg = load_voice_config()
    return {
        "ok": True,
        "voice": {
            **voice_cfg,
            "enabled": bool(voice_cfg.get("server_wake", False)),
            "providers": get_voice_providers(
                hermes_connected=HERMES_BRIDGE._connected,
                openclaw_connected=OPENCLAW_BRIDGE._connected,
                runtime=_active_runtime,
            ),
        },
    }


@app.post("/api/voice/config")
async def voice_config_post(req: VoiceConfigRequest):
    from alpha_os.voice.hermes_reload import reload_hermes_gateway

    voice_cfg = apply_voice_config(_voice_request_payload(req))
    await _restart_voice_loop()
    reload_result = await reload_hermes_gateway(
        HERMES_BRIDGE.gateway_url,
        hermes_connected=HERMES_BRIDGE._connected,
    )
    from alpha_os.voice import get_voice_providers
    return {
        "ok": True,
        "voice": {
            **voice_cfg,
            "enabled": bool(voice_cfg.get("server_wake", False)),
            "providers": get_voice_providers(
                hermes_connected=HERMES_BRIDGE._connected,
                openclaw_connected=OPENCLAW_BRIDGE._connected,
                runtime=_active_runtime,
            ),
        },
        "hermes_reload": reload_result,
    }


@app.post("/api/voice/tts")
async def voice_tts(req: TtsRequest):
    from alpha_os.voice.tts_stream import synthesize_tts

    result = await synthesize_tts(
        req.text,
        provider=req.provider,
        voice=req.voice,
        hermes_gateway_url=HERMES_BRIDGE.gateway_url,
        hermes_connected=HERMES_BRIDGE._connected,
    )
    if not result or not result.audio:
        return JSONResponse(
            status_code=502,
            content={"ok": False, "error": "TTS synthesis failed"},
        )
    return Response(content=result.audio, media_type=result.content_type)


@app.get("/api/voice/elevenlabs/voices")
async def voice_elevenlabs_voices(search: Optional[str] = None, page_size: int = 100):
    from alpha_os.voice.elevenlabs import list_elevenlabs_voices

    return await list_elevenlabs_voices(search=search, page_size=page_size)


@app.get("/api/voice/status")
async def voice_status():
    from alpha_os.voice.live import build_voice_live

    voice_cfg = load_voice_config()
    try:
        from alpha_os.voice import get_voice_providers, voice_available
        from alpha_os.voice.grok_oauth import grok_via_runtime_oauth

        available = voice_available()
        providers = get_voice_providers(
            hermes_connected=HERMES_BRIDGE._connected,
            openclaw_connected=OPENCLAW_BRIDGE._connected,
            runtime=_active_runtime,
        )
        grok_oauth = grok_via_runtime_oauth(
            hermes_connected=HERMES_BRIDGE._connected,
            openclaw_connected=OPENCLAW_BRIDGE._connected,
            runtime=_active_runtime,
        )
    except Exception:
        available = False
        providers = []
        grok_oauth = False
    live = build_voice_live()
    return {
        "server_voice": available and bool(voice_cfg.get("server_wake", False)),
        "browser_voice": bool(voice_cfg.get("browser_wake", True)),
        "wake_word": str(voice_cfg.get("wake_word", "hey alpha")),
        "wake_word_engine": "phrase",
        "grok_oauth": grok_oauth and bool(voice_cfg.get("grok_oauth", True)),
        "voice_via": live.get("tts_provider_label"),
        "hermes_config": voice_cfg.get("hermes_config_path"),
        "providers": providers,
        "live": live,
    }


@app.get("/api/voice/live")
async def voice_live():
    from alpha_os.voice.live import build_voice_live

    return {"ok": True, "live": build_voice_live()}


@app.post("/api/voice/usage")
async def voice_usage_report(req: VoiceUsageReport):
    from alpha_os.voice.live import build_voice_live
    from alpha_os.voice.usage import voice_usage_session

    kind = (req.kind or "").strip().lower()
    provider = (req.provider or "unknown").strip().lower()
    chars = max(0, req.characters)
    session = voice_usage_session()
    if kind == "stt":
        session.record_stt(provider=provider, characters=chars)
    elif kind == "tts":
        session.record_tts(provider=provider, characters=chars)
    else:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "kind must be tts or stt"},
        )
    return {"ok": True, "live": build_voice_live()}


@app.get("/api/hermes/status")
async def hermes_status():
    return HERMES_BRIDGE.get_status()


@app.get("/api/openclaw/status")
async def openclaw_status():
    return OPENCLAW_BRIDGE.get_status()


@app.get("/api/integrations")
async def integrations():
    return _build_integrations()


@app.get("/api/mcp")
async def api_mcp():
    return MCP_REGISTRY.get_panel_data()


@app.post("/api/mcp/refresh")
async def api_mcp_refresh():
    data = await MCP_REGISTRY.refresh(sample_data=True)
    return {"ok": True, "mcp": data}


class McpCallRequest(BaseModel):
    server: str
    tool: str
    arguments: Optional[dict[str, Any]] = None


@app.post("/api/mcp/call")
async def api_mcp_call(req: McpCallRequest):
    result = await MCP_REGISTRY.call_tool(req.server, req.tool, req.arguments)
    return result


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}…{value[-4:]}"


@app.get("/api/config")
async def api_config_get():
    from alpha_os.config import list_hermes_profiles, read_hermes_env
    from alpha_os.voice.hermes_sync import hermes_config_snapshot, load_voice_config

    cfg = load_config()
    hermes = cfg.get("hermes") or {}
    env = read_hermes_env()
    key = str(hermes.get("api_key") or "")
    if not key:
        key = env.get("API_SERVER_KEY") or env.get("HERMES_API_KEY") or ""

    voice = load_voice_config()
    el_key = env.get("ELEVENLABS_API_KEY") or ""
    return {
        **cfg,
        "hermes": {
            **hermes,
            "api_key_masked": _mask_secret(key),
            "api_key_set": bool(key),
            "profiles": list_hermes_profiles(),
            "profile": voice.get("hermes_profile") or hermes.get("profile"),
            "config_path": voice.get("hermes_config_path"),
            "snapshot": hermes_config_snapshot(),
        },
        "elevenlabs": {
            "api_key_masked": _mask_secret(el_key),
            "api_key_set": bool(el_key),
        },
        "voice_live": voice,
        "runtime_env": runtime_summary(),
        "tailscale_https_url": (
            f"https://{dns}" if (dns := _tailscale_dns_name()) else None
        ),
        "log_path": str(log_path()),
    }


def _sync_hermes_gateway_env(url: str, api_key: str) -> None:
    from urllib.parse import urlparse

    parsed = urlparse(url.strip())
    if not parsed.hostname:
        return
    env_updates: dict[str, str] = {
        "HERMES_GATEWAY_URL": url.rstrip("/"),
        "API_SERVER_HOST": parsed.hostname,
    }
    if parsed.port:
        env_updates["API_SERVER_PORT"] = str(parsed.port)
    if api_key:
        env_updates["API_SERVER_KEY"] = api_key
        env_updates["HERMES_API_KEY"] = api_key
    set_hermes_env(env_updates)


@app.post("/api/config")
async def api_config_post(req: ConfigRequest):
    if req.runtime:
        set_key("runtime", req.runtime)
    if req.hermes_gateway_url:
        set_key("hermes.gateway_url", req.hermes_gateway_url)
    if req.hermes_api_key:
        set_key("hermes.api_key", req.hermes_api_key)
    if req.openclaw_ws_url:
        set_key("openclaw.ws_url", req.openclaw_ws_url)
    if req.openclaw_token:
        set_key("openclaw.token", req.openclaw_token)
    if req.hermes_gateway_url:
        _sync_hermes_gateway_env(
            req.hermes_gateway_url,
            req.hermes_api_key or str(get("hermes.api_key", "")),
        )
    if req.elevenlabs_api_key:
        set_hermes_env({"ELEVENLABS_API_KEY": req.elevenlabs_api_key.strip()})
    await _init_bridges()
    return {"ok": True, "config": await api_config_get()}


@app.post("/api/config/autodetect")
async def api_config_autodetect():
    from alpha_os.runtime_sync import sync_runtime_config

    detected = await sync_runtime_config(sync_voice=True, only_missing=False)
    await _init_bridges()
    await _restart_voice_loop()
    return {"ok": True, "detected": detected, "config": await api_config_get()}


@app.post("/api/config/reload")
async def api_config_reload():
    """Re-read active config.yaml from disk (Hermes profile or OpenClaw home)."""
    from alpha_os.voice.hermes_sync import sync_voice_to_alpha_os

    voice = sync_voice_to_alpha_os()
    await _init_bridges()
    await _restart_voice_loop()
    return {"ok": True, "voice": voice, "config": await api_config_get()}


@app.get("/api/hermes/profiles")
async def api_hermes_profiles():
    from alpha_os.profile_config import list_profile_summaries

    return {"ok": True, "profiles": list_profile_summaries()}


@app.get("/api/hermes/profiles/{name}")
async def api_hermes_profile_detail(name: str):
    from alpha_os.profile_config import profile_summary

    summary = profile_summary(name)
    if not summary.get("config_path"):
        return JSONResponse(status_code=404, content={"ok": False, "error": "Profile not found"})
    return {"ok": True, "profile": summary}


@app.get("/api/hermes/profiles/{name}/voice")
async def api_hermes_profile_voice(name: str):
    from alpha_os.voice import get_voice_providers

    voice = load_voice_config(profile=name)
    return {
        "ok": True,
        "voice": {
            **voice,
            "enabled": bool(voice.get("server_wake", False)),
            "providers": get_voice_providers(
                hermes_connected=HERMES_BRIDGE._connected,
                openclaw_connected=OPENCLAW_BRIDGE._connected,
                runtime=_active_runtime,
            ),
        },
    }


@app.post("/api/hermes/profiles/switch")
async def api_hermes_profile_switch(req: ProfileSwitchRequest):
    from alpha_os.config import set_active_hermes_profile
    from alpha_os.voice.hermes_sync import sync_voice_to_alpha_os

    name = (req.profile or "").strip()
    if not name:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Profile name required"})
    set_active_hermes_profile(name)
    voice = sync_voice_to_alpha_os()
    await _restart_voice_loop()
    return {"ok": True, "profile": name, "voice": voice}


@app.post("/api/hermes/profiles/{name}/agent")
async def api_hermes_profile_agent(name: str, req: ProfileAgentRequest):
    from alpha_os.profile_config import apply_profile_agent_config
    from alpha_os.voice.hermes_reload import reload_hermes_gateway

    summary = apply_profile_agent_config(
        name,
        model_provider=req.model_provider,
        model_default=req.model_default,
        disabled_toolsets=req.disabled_toolsets,
        mcp_enabled=req.mcp_enabled,
    )
    reload_result = await reload_hermes_gateway(
        HERMES_BRIDGE.gateway_url,
        hermes_connected=HERMES_BRIDGE._connected,
    )
    return {"ok": True, "profile": summary, "hermes_reload": reload_result}


@app.get("/api/hermes/profiles/{name}/skills/{skill_path:path}")
async def api_hermes_profile_skill(name: str, skill_path: str):
    from alpha_os.profile_config import read_skill_markdown

    result = read_skill_markdown(name, skill_path)
    if not result.get("ok"):
        return JSONResponse(status_code=404, content=result)
    return result


@app.get("/api/system/info")
async def api_system_info():
    import platform

    uname = platform.uname()
    is_ubuntu = "ubuntu" in uname.system.lower() or "ubuntu" in uname.version.lower()
    return {
        "ok": True,
        "system": uname.system,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "ubuntu": is_ubuntu,
        "reboot_available": is_ubuntu,
    }


@app.post("/api/system/reboot")
async def api_system_reboot():
    import platform
    import subprocess

    uname = platform.uname()
    is_ubuntu = "ubuntu" in uname.system.lower() or "ubuntu" in uname.version.lower()
    if not is_ubuntu:
        return JSONResponse(
            status_code=403,
            content={"ok": False, "error": "Reboot is only available on Ubuntu"},
        )
    try:
        proc = subprocess.run(
            ["sudo", "-n", "reboot"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "error": proc.stderr.strip() or "sudo reboot failed (passwordless sudo required)",
                },
            )
        return {"ok": True, "detail": "Reboot initiated"}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})


@app.post("/api/reconnect")
async def api_reconnect():
    from alpha_os.runtime_sync import sync_runtime_config

    await sync_runtime_config(sync_voice=False, only_missing=True)
    await _init_bridges()
    return {"ok": True, "state": await _build_state()}


@app.websocket("/ws/state")
async def ws_state(ws: WebSocket):
    import hashlib
    import json

    from alpha_os.auth import auth_enabled, extract_token_from_websocket, token_valid

    if auth_enabled() and not token_valid(extract_token_from_websocket(ws)):
        await ws.close(code=4401)
        return

    await ws.accept()
    last_hash = ""
    idle_ticks = 0
    try:
        while True:
            await asyncio.sleep(0.5)
            data = await _build_state()
            payload = json.dumps(
                {
                    "event_seq": data.get("event_seq"),
                    "gateway_online": data.get("gateway_online"),
                    "hermes_connected": data.get("hermes_connected"),
                    "metrics": data.get("metrics"),
                    "capabilities": len(data.get("capabilities") or []),
                    "mcp": data.get("mcp", {}).get("tool_count"),
                },
                sort_keys=True,
                default=str,
            )
            digest = hashlib.md5(payload.encode()).hexdigest()
            if digest == last_hash:
                idle_ticks += 1
                if idle_ticks < 24:
                    continue
            else:
                idle_ticks = 0
                last_hash = digest
            await ws.send_json(data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket error: %s", e)


def main(host: str | None = None, port: int | None = None):
    import uvicorn

    port = port or int(get("server.port", 8080))
    host = host or str(get("server.host", "127.0.0.1"))
    uvicorn.run("alpha_os.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()