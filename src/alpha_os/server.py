"""Alpha OS FastAPI server."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from alpha_os.bridges.hermes_bridge import HermesBridge
from alpha_os.bridges.openclaw_bridge import OpenClawBridge
from alpha_os.bridges.detector import (
    detect_best,
    detect_hermes,
    detect_openclaw,
    hermes_installed,
    openclaw_installed,
)
from alpha_os.config import get, load_config, set_hermes_env, set_key
from alpha_os.voice.hermes_sync import apply_voice_config, load_voice_config
from alpha_os.core.alpha import Alpha
from alpha_os.core.events import LiveEventBuffer
from alpha_os.integrations.mcp_bridge import MCPRegistry
from alpha_os.integrations.tailscale import TailscaleStatus

logger = logging.getLogger("alpha_os.server")

STATIC_DIR = Path(__file__).parent / "dashboard" / "static"
HERMES_HOME = Path.home() / ".hermes"

ALPHA = Alpha()


def _is_live() -> bool:
    """Live when the active runtime gateway is connected. No demo data while offline."""
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
            "events_per_min": 0,
        },
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
            "self_ip": None,
            "hostname": None,
            "exit_node": None,
            "peers": [],
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
    cfg = load_config()
    runtime_pref = str(cfg.get("runtime", "auto")).lower()

    hermes_info, openclaw_info = await asyncio.gather(
        detect_hermes(),
        detect_openclaw(),
    )

    if hermes_info.gateway_url:
        HERMES_BRIDGE.gateway_url = hermes_info.gateway_url
    if hermes_info.api_key:
        HERMES_BRIDGE.api_key = hermes_info.api_key
    if openclaw_info.ws_url:
        OPENCLAW_BRIDGE.ws_url = openclaw_info.ws_url
    elif openclaw_info.gateway_url:
        OPENCLAW_BRIDGE.ws_url = openclaw_info.gateway_url.replace(
            "http://", "ws://"
        ).replace("https://", "wss://")
    if openclaw_info.api_key:
        OPENCLAW_BRIDGE.token = openclaw_info.api_key

    target = runtime_pref
    if target == "auto":
        best = await detect_best()
        target = best.name if best.name in ("hermes", "openclaw") else "offline"

    if target == "hermes":
        ok = await HERMES_BRIDGE.connect()
        _active_runtime = "hermes" if ok else "offline"
        logger.info("Hermes gateway %s", "connected" if ok else "offline")
    elif target == "openclaw":
        ok = await OPENCLAW_BRIDGE.connect()
        _active_runtime = "openclaw" if ok else "offline"
        logger.info("OpenClaw gateway %s", "connected" if ok else "offline")
    else:
        _active_runtime = "offline"
        logger.info("No runtime connected — panels will start empty")


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


async def _build_state() -> dict[str, Any]:
    global _last_hermes_retry, _last_oc_retry, _active_runtime
    now = time.time()

    if _active_runtime == "hermes":
        if not HERMES_BRIDGE._connected and now - _last_hermes_retry > 30:
            _last_hermes_retry = now
            await HERMES_BRIDGE.connect()
    elif _active_runtime == "openclaw":
        if not OPENCLAW_BRIDGE._connected and now - _last_oc_retry > 30:
            _last_oc_retry = now
            await OPENCLAW_BRIDGE.connect()

    agents: list[dict] = []
    if _active_runtime == "hermes" and HERMES_BRIDGE._connected:
        agents = HERMES_BRIDGE.get_agent_list() or []
    elif _active_runtime == "openclaw" and OPENCLAW_BRIDGE._connected:
        agents = OPENCLAW_BRIDGE.get_agent_list() or []

    live = _is_live()
    cfg = load_config()

    data = ALPHA.get_dashboard_state(
        hermes_agents=agents if live else None,
        runtime=_active_runtime,
    )
    data["hermes"] = HERMES_BRIDGE.get_status()
    data["openclaw"] = OPENCLAW_BRIDGE.get_status()
    data["hermes_installed"] = hermes_installed()
    data["openclaw_installed"] = openclaw_installed()
    data["hermes_connected"] = HERMES_BRIDGE._connected
    data["openclaw_connected"] = OPENCLAW_BRIDGE._connected
    data["runtime_preference"] = str(cfg.get("runtime", "auto"))
    data["runtimes"] = {
        "hermes": {
            "installed": hermes_installed(),
            "connected": HERMES_BRIDGE._connected,
            "gateway_url": HERMES_BRIDGE.gateway_url,
        },
        "openclaw": {
            "installed": openclaw_installed(),
            "connected": OPENCLAW_BRIDGE._connected,
            "ws_url": OPENCLAW_BRIDGE.ws_url,
        },
    }
    data["live"] = live

    if not live:
        data.update(_empty_panel_state())
    else:
        data["integrations"] = _build_integrations()
        data["tailscale"] = TAILSCALE.to_dict()
        toolsets = data["integrations"].get("toolsets", [])
        mcp_data = MCP_REGISTRY.get_panel_data()
        tool_count = sum(
            len(ts.get("tools", [])) if isinstance(ts, dict) else 0 for ts in toolsets
        )
        if not tool_count and mcp_data.get("tool_count"):
            tool_count = int(mcp_data["tool_count"])

        data["metrics"] = {
            "sessions": len(data["integrations"].get("sessions", [])),
            "agents": len(agents),
            "tools": tool_count or len(toolsets),
            "toolsets": len(toolsets),
            "skills": len(data["integrations"].get("skills", [])),
            "events_per_min": LIVE_EVENTS.events_per_minute(),
        }
        data["polymarket"] = _polymarket_metrics(mcp_data)
        data["live_events"] = LIVE_EVENTS.get_recent(20)
        data["event_seq"] = LIVE_EVENTS.latest_seq()
        data["orb_pulse"] = LIVE_EVENTS.consume_pulse()
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
    return data


def _on_gateway_event(source: str, event: dict[str, Any]) -> None:
    LIVE_EVENTS.push(source, event)
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
            await MCP_REGISTRY.refresh()
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
    await _init_bridges()
    _start_event_streams()
    asyncio.create_task(_tailscale_loop())
    asyncio.create_task(_mcp_refresh_loop())
    await MCP_REGISTRY.refresh()
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
        await asyncio.sleep(60)


app = FastAPI(title="Alpha OS", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ],
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
    openclaw_ws_url: Optional[str] = None
    openclaw_token: Optional[str] = None


class VoiceConfigRequest(BaseModel):
    wake_word: Optional[str] = None
    browser_wake: Optional[bool] = None
    server_wake: Optional[bool] = None
    enabled: Optional[bool] = None  # alias for server_wake
    grok_oauth: Optional[bool] = None
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
    provider_id: Optional[str] = None
    provider_enabled: Optional[bool] = None


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
        LIVE_EVENTS.push("command", {"type": "command", "text": cmd, "reply": reply[:120]})
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
    voice_cfg = apply_voice_config(_voice_request_payload(req))
    await _restart_voice_loop()
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
    }


@app.get("/api/voice/status")
async def voice_status():
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
    return {
        "server_voice": available and bool(voice_cfg.get("server_wake", False)),
        "browser_voice": bool(voice_cfg.get("browser_wake", True)),
        "wake_word": str(voice_cfg.get("wake_word", "hey alpha")),
        "wake_word_engine": "phrase",
        "grok_oauth": grok_oauth and bool(voice_cfg.get("grok_oauth", True)),
        "voice_via": "hermes_grok_oauth",
        "hermes_config": voice_cfg.get("hermes_config_path"),
        "providers": providers,
    }


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
    data = await MCP_REGISTRY.refresh()
    return {"ok": True, "mcp": data}


@app.get("/api/config")
async def api_config_get():
    return load_config()


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
    await _init_bridges()
    return {"ok": True, "config": load_config()}


@app.websocket("/ws/state")
async def ws_state(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await _build_state()
            await ws.send_json(data)
            seq = data.get("event_seq", 0)
            for _ in range(20):
                await asyncio.sleep(0.1)
                if LIVE_EVENTS.latest_seq() > seq:
                    break
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