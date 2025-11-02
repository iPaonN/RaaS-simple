"""Base repository contracts used across persistence implementations."""

from __future__ import annotations

from typing import Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)


class Repository(Protocol[T_co]):
    """Generic repository protocol."""

    async def add(self, entity: T_co) -> T_co:
        ...

    async def list(self) -> list[T_co]:
        ...
