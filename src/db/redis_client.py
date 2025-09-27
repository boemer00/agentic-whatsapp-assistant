from redis.asyncio import Redis
from src.core.config import settings

_redis: Redis | None = None

async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _redis
