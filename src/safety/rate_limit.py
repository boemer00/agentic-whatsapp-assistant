from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass
class RateLimitOutcome:
    allowed: bool
    remaining: int
    limit: int
    reset_seconds: int

class RateLimitError(Exception):
    pass

async def fixed_window_allow(
    redis: Redis, key: str, limit: int, window_seconds: int
) -> RateLimitOutcome:
    """
    Fixed-window counter: INCR + set EXPIRE on first hit.
    Returns whether the call is allowed and remaining quota.
    """
    if limit <= 0:
        return RateLimitOutcome(True, limit, limit, window_seconds)

    pipe = redis.pipeline()
    pipe.incr(key, 1)
    pipe.ttl(key)
    count, ttl = await pipe.execute()

    # If first increment (ttl == -1), set expiry
    if ttl == -1:
        await redis.expire(key, window_seconds)
        ttl = window_seconds

    remaining = max(0, limit - int(count))
    return RateLimitOutcome(allowed=int(count) <= limit, remaining=remaining, limit=limit, reset_seconds=int(ttl))
