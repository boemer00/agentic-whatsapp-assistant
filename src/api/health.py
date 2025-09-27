from fastapi import APIRouter
from pydantic import BaseModel

from src.db.redis_client import get_redis

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str = "ai-assistant"
    version: str = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    # Liveness probe
    return HealthResponse(status="ok")


@router.get("/health/ready")
async def ready() -> dict:
    r = await get_redis()
    await r.set("healthcheck", "ok", ex=10)
    val = await r.get("healthcheck")
    return {"status": "ok", "redis": val == "ok"}
