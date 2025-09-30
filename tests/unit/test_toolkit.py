"""Unit tests for toolkit helper functions."""

import anyio
from pydantic import BaseModel

from src.core.config import settings
from src.safety.rate_limit import RateLimitOutcome
from src.tools.base import ToolContext
from src.tools.toolkit import call_tool, register


class ExampleIn(BaseModel):
    value: int


class ExampleOut(BaseModel):
    value: int


class AlternateOut(BaseModel):
    value: int


class ExampleTool:
    name = "example.tool"
    input_model = ExampleIn
    output_model = ExampleOut

    async def __call__(self, args: ExampleIn, ctx: ToolContext) -> dict[str, int]:
        return {"value": args.value}


async def _invoke_with_expected_model() -> AlternateOut:
    result = await call_tool(
        "example.tool",
        {"value": 3},
        ToolContext(session_id="s"),
        expected_model=AlternateOut,
    )
    assert isinstance(result, AlternateOut)
    return result


def test_call_tool_with_expected_model(monkeypatch) -> None:
    monkeypatch.setattr("src.tools.toolkit._REGISTRY", {}, raising=False)
    register(ExampleTool())

    original_allowlist = settings.tool_allowlist_raw
    monkeypatch.setattr(settings, "tool_allowlist_raw", "example.tool", raising=False)

    class _Pipe:
        def incr(self, *args, **kwargs):
            return None

        def ttl(self, *args, **kwargs):
            return None

        async def execute(self):
            return 1, -1

    class _FakeRedis:
        def pipeline(self):  # type: ignore[override]
            return _Pipe()

        async def expire(self, *args, **kwargs):
            return True

    async def _fake_get_redis():
        return _FakeRedis()

    async def _fake_fixed_window_allow(*args, **kwargs) -> RateLimitOutcome:
        return RateLimitOutcome(True, remaining=1, limit=1, reset_seconds=0)

    monkeypatch.setattr("src.tools.toolkit.get_redis", _fake_get_redis, raising=False)
    monkeypatch.setattr("src.tools.toolkit.fixed_window_allow", _fake_fixed_window_allow, raising=False)

    try:
        result = anyio.run(_invoke_with_expected_model)
        assert result.value == 3
    finally:
        settings.tool_allowlist_raw = original_allowlist
