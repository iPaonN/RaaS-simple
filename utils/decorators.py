"""Custom decorators shared across the project."""

from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

TFunc = TypeVar("TFunc", bound=Callable[..., Awaitable[Any]])


def log_exceptions(logger):
    """Decorator that logs exceptions raised by async functions."""

    def decorator(func: TFunc) -> TFunc:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):  # type: ignore[misc]
            try:
                return await func(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - utility hook
                logger.exception("Unhandled error in %s", func.__name__, exc_info=exc)
                raise

        return wrapper  # type: ignore[return-value]

    return decorator