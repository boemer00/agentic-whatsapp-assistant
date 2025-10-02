"""Tracing utilities with optional LangSmith integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, overload

try:
    from langsmith import traceable as _traceable  # type: ignore
except ImportError:  # pragma: no cover - executed when LangSmith missing
    F = TypeVar("F", bound=Callable[..., Any])

    @overload
    def traceable(func: F) -> F:  # type: ignore[misc]
        ...

    @overload
    def traceable(*, name: str | None = None) -> Callable[[F], F]:
        ...

    def traceable(*args: Any, **kwargs: Any):  # type: ignore[override]
        """No-op decorator used when LangSmith is unavailable."""

        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def decorator(func: F) -> F:
            return func

        return decorator
else:  # pragma: no cover - exercised when LangSmith installed
    traceable = _traceable

__all__ = ["traceable"]

