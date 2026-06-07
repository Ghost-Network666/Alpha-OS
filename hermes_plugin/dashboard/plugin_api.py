"""Optional FastAPI routes mounted at /api/plugins/alpha-os/ by Hermes dashboard."""

import os

import httpx
from fastapi import APIRouter

router = APIRouter()

_ALPHA_PORT = int(os.getenv("ALPHA_OS_PORT", "8080"))
_ALPHA_HOST = os.getenv("ALPHA_OS_HOST", "127.0.0.1")


@router.get("/health")
async def plugin_health():
    return {"plugin": "alpha-os", "status": "ok", "version": "0.1.0"}


@router.get("/proxy/state")
async def proxy_state():
    """Proxy Alpha OS state for Hermes dashboard plugin (avoids CORS in some setups)."""
    url = f"http://{_ALPHA_HOST}:{_ALPHA_PORT}/api/state"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return {"runtime": "offline", "hermes_connected": False, "openclaw_connected": False}