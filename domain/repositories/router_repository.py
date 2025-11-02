"""Router repository interface."""

from __future__ import annotations

from typing import Protocol

from domain.entities.router import Router


class RouterRepository(Protocol):
    """Abstract persistence layer for router entities."""

    async def add(self, router: Router) -> Router:
        ...

    async def list(self) -> list[Router]:
        ...

    async def get_by_host(self, host: str) -> Router | None:
        ...
