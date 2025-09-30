import anyio
from src.db.redis_client import get_redis
from src.safety.rate_limit import fixed_window_allow

def test_fixed_window_allows_then_blocks():
    async def run():
        r = await get_redis()
        key = "test:rl:unit"
        # Clean slate
        await r.delete(key)
        # Allow 2 per 5 seconds
        out1 = await fixed_window_allow(r, key, 2, 5); assert out1.allowed
        out2 = await fixed_window_allow(r, key, 2, 5); assert out2.allowed
        out3 = await fixed_window_allow(r, key, 2, 5); assert not out3.allowed
    anyio.run(run)
