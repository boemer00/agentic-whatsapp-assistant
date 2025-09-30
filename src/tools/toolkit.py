import inspect
from typing import Dict, Optional, Type

from pydantic import BaseModel

from src.core.config import settings
from src.db.redis_client import get_redis
from src.safety.rate_limit import RateLimitError, fixed_window_allow

from .base import Tool, ToolContext

_REGISTRY: Dict[str, Tool] = {}

def register(tool: Tool) -> None:
    if tool.name in _REGISTRY:
        raise ValueError(f"Duplicate tool: {tool.name}")
    _REGISTRY[tool.name] = tool

async def call_tool(
    name: str,
    payload: dict,
    ctx: ToolContext,
    *,
    expected_model: Optional[Type[BaseModel]] = None,
) -> BaseModel:
    # Allow-list
    if name not in settings.tool_allowlist:
        raise PermissionError(f"Tool '{name}' is not allowed")

    tool = _REGISTRY[name]
    args = tool.input_model(**payload)  # validate in

    # Rate limit (per session/user, per tool)
    r = await get_redis()
    principal = ctx.user_id or ctx.session_id or "anon"
    rl_key = f"rl:tool:{name}:{principal}"
    outcome = await fixed_window_allow(r, rl_key, settings.rate_limit_tool_per_min, 60)
    if not outcome.allowed:
        raise RateLimitError(f"Rate limit exceeded for {name}. Try again in {outcome.reset_seconds}s.")

    # Execute (supports sync or async __call__)
    result = tool(args, ctx)
    if inspect.isawaitable(result):
        result = await result

    model = expected_model or tool.output_model
    return model.model_validate(result)  # validate out
