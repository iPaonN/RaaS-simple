"""Business logic for managing routers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from domain.entities.router import Router
from domain.repositories.router_repository import RouterRepository


class RouterService:
    """Coordinates router CRUD operations."""

    def __init__(self, repository: RouterRepository) -> None:
        self._repository = repository

    async def register_router(self, router: Router) -> Router:
        return await self._repository.add(router)

    async def list_routers(self) -> Iterable[Router]:
        return await self._repository.list()

    async def export_inventory(self) -> list[dict[str, object]]:
        routers = await self._repository.list()
        return [asdict(router) for router in routers]
