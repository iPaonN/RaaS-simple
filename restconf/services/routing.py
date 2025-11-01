"""Routing-related RESTCONF operations."""
from __future__ import annotations

from typing import Dict, List

from restconf.models import RoutingTable, StaticRoute

from .base import RestconfDomainService


class RoutingService(RestconfDomainService):
    """Operations focused on routing datasets."""

    async def fetch_routing_table(self) -> RoutingTable:
        payload = await self.client.get("ietf-routing:routing")
        routes_payload = payload.get("ietf-routing:routing", {})
        static_routes = self._extract_static_routes(routes_payload)
        return RoutingTable.from_routes(static_routes)

    async def fetch_static_routes(self) -> List[StaticRoute]:
        payload = await self.client.get("Cisco-IOS-XE-native:native/ip/route")
        routes_payload = payload.get("Cisco-IOS-XE-native:route", [])
        return self._parse_static_routes(routes_payload)

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
