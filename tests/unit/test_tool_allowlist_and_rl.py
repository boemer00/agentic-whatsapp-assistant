import anyio
from pydantic import BaseModel
from src.tools.base import Tool, ToolContext
from src.tools.toolkit import register, call_tool
from src.core.config import settings
from src.db.redis_client import get_redis
from src.safety.rate_limit import RateLimitError

# Dummy tool
class EchoIn(BaseModel):
    text: str

class EchoOut(BaseModel):
    text: str

class EchoTool:
    name = "echo.tool"
    input_model = EchoIn
    output_model = EchoOut
    async def __call__(self, args: EchoIn, ctx: ToolContext) -> EchoOut:
        return EchoOut(text=args.text)

# Register once
try:
    register(EchoTool())  # may raise if duplicate in repeated runs
except Exception:
    pass

def test_allowlist_blocks_unlisted_tool(monkeypatch):
    # Force allowlist to not include echo.tool
    monkeypatch.setenv("TOOL_ALLOWLIST", "weather.get")
    from importlib import reload
    from src.core import config
    reload(config)
    async def run():
        try:
            await call_tool("echo.tool", {"text":"x"}, ToolContext(session_id="s"))
            assert False, "should have raised PermissionError"
        except PermissionError:
            assert True
    anyio.run(run)

def test_tool_rate_limit(monkeypatch):
    async def run():
        # Ensure echo.tool is allowed for this test
        from importlib import reload
        from src.core import config
        import os

        original_allowlist = os.environ.get("TOOL_ALLOWLIST")
        original_rate_limit = os.environ.get("RATE_LIMIT_TOOL_PER_MIN")

        os.environ["TOOL_ALLOWLIST"] = "weather.get,echo.tool"
        reload(config)
        monkeypatch.setattr("src.tools.toolkit.settings", config.settings, raising=False)

        r = await get_redis()
        await r.flushdb()

        # low limit for test
        os.environ["RATE_LIMIT_TOOL_PER_MIN"] = "2"
        reload(config)
        monkeypatch.setattr("src.tools.toolkit.settings", config.settings, raising=False)

        try:
            await call_tool("echo.tool", {"text":"a"}, ToolContext(session_id="s"))
            await call_tool("echo.tool", {"text":"b"}, ToolContext(session_id="s"))
            try:
                await call_tool("echo.tool", {"text":"c"}, ToolContext(session_id="s"))
                assert False, "expected RateLimitError"
            except RateLimitError:
                assert True
        finally:
            if original_allowlist is None:
                os.environ.pop("TOOL_ALLOWLIST", None)
            else:
                os.environ["TOOL_ALLOWLIST"] = original_allowlist
            if original_rate_limit is None:
                os.environ.pop("RATE_LIMIT_TOOL_PER_MIN", None)
            else:
                os.environ["RATE_LIMIT_TOOL_PER_MIN"] = original_rate_limit
            reload(config)
            monkeypatch.setattr("src.tools.toolkit.settings", config.settings, raising=False)
    anyio.run(run)
