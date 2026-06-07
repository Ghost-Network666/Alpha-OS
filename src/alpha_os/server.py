"""Alpha OS FastAPI server."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from alpha_os.bridges.hermes_bridge import HermesBridge
from alpha_os.bridges.openclaw_bridge import OpenClawBridge
from alpha_os.bridges.detector import detect_best
from alpha_os.config import get, load_config, set_key
from alpha_os.core.alpha import Alpha
from alpha_os.core.events import LiveEventBuffer
from alpha_os.integrations.mcp_bridge import MCPRegistry
from alpha_os.integrations.tailscale import TailscaleStatus

logger = logging.getLogger("alpha_os.server")

STATIC_DIR = Path(__file__).parent / "dashboard" / "static"

ALPHA = Alpha()
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
    info = await detect_best()
    if info.name == "hermes" and info.gateway_url:
        HERMES_BRIDGE.gateway_url = info.gateway_url
        if info.api_key:
            HERMES_BRIDGE.api_key = info.api_key
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

    data = ALPHA.get_dashboard_state(hermes_agents=agents or None, runtime=_active_runtime)
    data["hermes"] = HERMES_BRIDGE.get_status()
    data["openclaw"] = OPENCLAW_BRIDGE.get_status()
    data["hermes_connected"] = HERMES_BRIDGE._connected
    data["openclaw_connected"] = OPENCLAW_BRIDGE._connected
    data["integrations"] = _build_integrations()
    data["tailscale"] = TAILSCALE.to_dict()
    data["metrics"] = {
        "sessions": len(data["integrations"].get("sessions", [])),
        "agents": len(agents),
        "toolsets": len(data["integrations"].get("toolsets", [])),
        "skills": len(data["integrations"].get("skills", [])),
    }
    data["live_events"] = LIVE_EVENTS.get_recent(20)
    data["event_seq"] = LIVE_EVENTS.latest_seq()
    data["orb_pulse"] = LIVE_EVENTS.consume_pulse()
    data["mcp"] = MCP_REGISTRY.get_panel_data()
    data["voice_config"] = {
        "enabled": bool(get("voice.enabled", False)),
        "wake_word": str(get("voice.wake_word", "hey alpha")),
        "browser_mic": True,
    }
    return data


def _on_gateway_event(source: str, event: dict[str, Any]) -> None:
    LIVE_EVENTS.push(source, event)
    summary = LIVE_EVENTS.get_recent(1)
    if summary:
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


async def _start_voice_loop() -> None:
    global _voice_loop
    if not get("voice.enabled", False):
        return
    try:
        from alpha_os.voice import VoiceLoop

        async def on_transcript(text: str) -> None:
            reply = ALPHA.process(text)
            LIVE_EVENTS.push("voice", {"type": "transcript", "text": text, "reply": reply})

        _voice_loop = VoiceLoop(
            wake_word=str(get("voice.wake_word", "hey alpha")),
            on_transcript=on_transcript,
        )
        await _voice_loop.start()
    except Exception as e:
        logger.warning("Voice loop unavailable: %s", e)


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
    if _voice_loop:
        await _voice_loop.stop()
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


@app.get("/api/voice/status")
async def voice_status():
    try:
        from alpha_os.voice import voice_available
        available = voice_available()
    except Exception:
        available = False
    return {
        "server_voice": available and bool(get("voice.enabled", False)),
        "browser_voice": True,
        "wake_word": str(get("voice.wake_word", "hey alpha")),
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