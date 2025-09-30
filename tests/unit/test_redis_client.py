"""Unit tests for Redis client helper."""

import anyio

from src.db.redis_client import get_redis


def test_get_redis_recreates_on_new_loop(monkeypatch) -> None:
    creations: list[object] = []

    def _fake_from_url(*args, **kwargs):
        instance = object()
        creations.append(instance)
        return instance

    monkeypatch.setattr("src.db.redis_client.Redis.from_url", _fake_from_url, raising=False)
    monkeypatch.setattr("src.db.redis_client._redis", None, raising=False)
    monkeypatch.setattr("src.db.redis_client._redis_loop", None, raising=False)

    async def _same_loop() -> object:
        first = await get_redis()
        second = await get_redis()
        assert first is second
        return first

    first_client = anyio.run(_same_loop)

    async def _single_call() -> object:
        return await get_redis()

    second_client = anyio.run(_single_call)

    assert first_client is not second_client
    assert len(creations) >= 2
