"""Use case for registering routers in the system."""

from __future__ import annotations

from domain.entities.router import Router
from domain.services.router_service import RouterService


class AddRouterUseCase:
    """Coordinate router registration with validation hooks."""

    def __init__(self, service: RouterService) -> None:
        self._service = service

    async def execute(self, router: Router) -> Router:
        return await self._service.register_router(router)
