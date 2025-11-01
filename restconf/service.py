"""Domain service implementing high-level RESTCONF operations."""
from __future__ import annotations

from restconf.client import RestconfClient
from restconf.models import Hostname, Interface, RoutingTable, StaticRoute
from restconf.services import DeviceService, InterfaceService, RoutingService


class RestconfService:
    """Facade that coordinates smaller RESTCONF services."""

    def __init__(self, client: RestconfClient) -> None:
        self._client = client
        self.interfaces = InterfaceService(client)
        self.device = DeviceService(client)
        self.routing = RoutingService(client)

    @property
    def client(self) -> RestconfClient:
        """Expose underlying RESTCONF client."""
        return self._client

    # ------------------------------------------------------------------
    # Delegating helpers for backwards compatibility
    # ------------------------------------------------------------------
    async def fetch_interfaces(self) -> list[Interface]:
        return await self.interfaces.fetch_interfaces()

    async def fetch_interface(self, name: str) -> Interface:
        return await self.interfaces.fetch_interface(name)

    async def update_interface_description(self, name: str, description: str) -> Interface:
        return await self.interfaces.update_interface_description(name, description)

    async def update_interface_state(self, name: str, enabled: bool) -> Interface:
        return await self.interfaces.update_interface_state(name, enabled)

    async def update_interface_ip(self, name: str, ip: str, netmask: str) -> Interface:
        return await self.interfaces.update_interface_ip(name, ip, netmask)

    async def fetch_hostname(self) -> Hostname:
        return await self.device.fetch_hostname()

    async def update_hostname(self, hostname: str) -> Hostname:
        return await self.device.update_hostname(hostname)

    async def fetch_routing_table(self) -> RoutingTable:
        return await self.routing.fetch_routing_table()

    async def fetch_static_routes(self) -> list[StaticRoute]:
        return await self.routing.fetch_static_routes()
