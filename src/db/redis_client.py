from __future__ import annotations

import asyncio
from typing import Optional

from redis.asyncio import Redis
from src.core.config import settings

_redis: Optional[Redis] = None
_redis_loop: Optional[asyncio.AbstractEventLoop] = None


async def get_redis() -> Redis:
    global _redis, _redis_loop
    loop = asyncio.get_running_loop()
    if _redis is None or _redis_loop is not loop:
        _redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        _redis_loop = loop
    return _redis
