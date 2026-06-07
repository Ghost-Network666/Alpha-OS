"""Optional FastAPI routes mounted at /api/plugins/alpha-os/ by Hermes dashboard."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def plugin_health():
    return {"plugin": "alpha-os", "status": "ok", "version": "0.1.0"}