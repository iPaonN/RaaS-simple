"""Database abstraction layer interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DatabaseSession(Protocol):
    """Minimal contract for persistence sessions."""

    async def __aenter__(self) -> "DatabaseSession":
        ...

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        ...


class DatabaseGateway(Protocol):
    """Protocol describing the capabilities required by domain services."""

    async def acquire(self) -> DatabaseSession:
        ...
