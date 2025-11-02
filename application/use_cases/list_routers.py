"""Use case for listing routers."""

from __future__ import annotations

from typing import Iterable

from domain.entities.router import Router
from domain.services.router_service import RouterService


class ListRoutersUseCase:
    """Provide a read-only view over registered routers."""

    def __init__(self, service: RouterService) -> None:
        self._service = service

    async def execute(self) -> Iterable[Router]:
        return await self._service.list_routers()
