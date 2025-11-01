"""Domain service implementing high-level RESTCONF operations."""
from __future__ import annotations

from typing import Dict, List

from restconf.client import RestconfClient
from restconf.errors import RestconfHTTPError, RestconfNotFoundError
from restconf.models import (
    Hostname,
    Interface,
    InterfaceAddress,
    RoutingTable,
    StaticRoute,
)
from utils.logger import get_logger

_logger = get_logger(__name__)


class RestconfService:
    """Business logic for RESTCONF interactions."""

    def __init__(self, client: RestconfClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Interface operations
    # ------------------------------------------------------------------
    async def fetch_interfaces(self) -> List[Interface]:
        payload = await self._client.get("ietf-interfaces:interfaces")
        interfaces = (
            payload.get("ietf-interfaces:interfaces", {}).get("interface", [])
        )
        return [self._parse_interface(raw) for raw in interfaces]

    async def fetch_interface(self, name: str) -> Interface:
        try:
            payload = await self._client.get(f"ietf-interfaces:interfaces/interface={name}")
        except RestconfNotFoundError as exc:
            raise RestconfNotFoundError(status=exc.status, message=f"Interface '{name}' not found", details=exc.details)

        interface_payload = payload.get("ietf-interfaces:interface")
        if not interface_payload:
            raise RestconfNotFoundError(status=404, message=f"Interface '{name}' not found")
        return self._parse_interface(interface_payload)

    async def update_interface_description(self, name: str, description: str) -> Interface:
        await self._client.patch(
            f"ietf-interfaces:interfaces/interface={name}",
            data={
                "ietf-interfaces:interface": {
                    "name": name,
                    "description": description,
                    "type": "iana-if-type:ethernetCsmacd",
                }
            },
        )
        _logger.info("Updated description on interface %s", name)
        return await self.fetch_interface(name)

    async def update_interface_state(self, name: str, enabled: bool) -> Interface:
        await self._client.patch(
            f"ietf-interfaces:interfaces/interface={name}",
            data={
                "ietf-interfaces:interface": {
                    "name": name,
                    "enabled": enabled,
                    "type": "iana-if-type:ethernetCsmacd",
                }
            },
        )
        _logger.info("Set interface %s state to %s", name, enabled)
        return await self.fetch_interface(name)

    async def update_interface_ip(self, name: str, ip: str, netmask: str) -> Interface:
        await self._client.patch(
            f"ietf-interfaces:interfaces/interface={name}",
            data={
                "ietf-interfaces:interface": {
                    "name": name,
                    "type": "iana-if-type:ethernetCsmacd",
                    "ietf-ip:ipv4": {
                        "address": [
                            {
                                "ip": ip,
                                "netmask": netmask,
                            }
                        ]
                    },
                }
            },
        )
        _logger.info("Updated IP %s/%s on interface %s", ip, netmask, name)
        return await self.fetch_interface(name)

    # ------------------------------------------------------------------
    # Hostname operations
    # ------------------------------------------------------------------
    async def fetch_hostname(self) -> Hostname:
        payload = await self._client.get("Cisco-IOS-XE-native:native/hostname")
        value = payload.get("Cisco-IOS-XE-native:hostname")
        if not value:
            raise RestconfHTTPError(status=500, message="Hostname missing in payload")
        return Hostname(value=value)

    async def update_hostname(self, hostname: str) -> Hostname:
        await self._client.patch(
            "Cisco-IOS-XE-native:native/hostname",
            data={"Cisco-IOS-XE-native:hostname": hostname},
        )
        _logger.info("Updated hostname to %s", hostname)
        return Hostname(value=hostname)

    # ------------------------------------------------------------------
    # Routing operations
    # ------------------------------------------------------------------
    async def fetch_routing_table(self) -> RoutingTable:
        payload = await self._client.get("ietf-routing:routing")
        routes_payload = payload.get("ietf-routing:routing", {})
        static_routes = self._extract_static_routes(routes_payload)
        return RoutingTable.from_routes(static_routes)

    async def fetch_static_routes(self) -> List[StaticRoute]:
        payload = await self._client.get("Cisco-IOS-XE-native:native/ip/route")
        routes_payload = payload.get("Cisco-IOS-XE-native:route", [])
        return self._parse_static_routes(routes_payload)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def _parse_interface(self, payload: Dict[str, object]) -> Interface:
        addresses_payload = (
            (
                payload.get("ietf-ip:ipv4", {})
                if isinstance(payload.get("ietf-ip:ipv4"), dict)
                else {}
            )
            .get("address", [])
        )

        addresses = [
            InterfaceAddress(
                ip=str(entry.get("ip", "")),
                netmask=str(entry.get("netmask", "")),
            )
            for entry in addresses_payload
            if isinstance(entry, dict)
        ]

        return Interface(
            name=str(payload.get("name", "unknown")),
            enabled=bool(payload.get("enabled", False)),
            type=str(payload.get("type", "unknown")),
            description=str(payload.get("description")) if payload.get("description") else None,
            ipv4_addresses=addresses,
        )

    def _extract_static_routes(self, payload: Dict[str, object]) -> List[StaticRoute]:
        routes: List[StaticRoute] = []
        static = payload.get("ietf-routing:static")
        if isinstance(static, dict):
            ribs = static.get("route")
            if isinstance(ribs, list):
                for route_entry in ribs:
                    if not isinstance(route_entry, dict):
                        continue
                    destination = route_entry.get("destination-prefix", "unknown")
                    next_hops = route_entry.get("next-hop", {})
                    next_hop_address = "unknown"
                    if isinstance(next_hops, dict):
                        ipv4_next = next_hops.get("outgoing-interface") or next_hops.get("next-hop-address")
                        if isinstance(ipv4_next, str):
                            next_hop_address = ipv4_next
                    routes.append(StaticRoute(prefix=str(destination), next_hop=str(next_hop_address)))
        return routes

    def _parse_static_routes(self, payload: object) -> List[StaticRoute]:
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            return []
        routes: List[StaticRoute] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            prefix = entry.get("prefix") or entry.get("ip-prefix") or "unknown"
            next_hop = entry.get("next-hop") or entry.get("fwd") or "unknown"
            routes.append(StaticRoute(prefix=str(prefix), next_hop=str(next_hop)))
        return routes
