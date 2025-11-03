"""Routing-related RESTCONF operations."""
from __future__ import annotations

import ipaddress
from typing import Dict, List, Tuple

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
        routes_payload = payload.get("Cisco-IOS-XE-native:route")
        return self._parse_static_routes(routes_payload)

    async def add_static_route(self, prefix: str, netmask: str, next_hop: str) -> StaticRoute:
        """Configure a static route on the target device."""

        dotted_mask, cidr = self._normalize_netmask(netmask)
        endpoint = (
            "Cisco-IOS-XE-native:native/ip/route/ip-route-interface-forwarding-list="
            f"{prefix},{dotted_mask}"
        )
        body = {
            "Cisco-IOS-XE-native:ip-route-interface-forwarding-list": {
                "prefix": prefix,
                "mask": dotted_mask,
                "fwd-list": [
                    {
                        "fwd": next_hop,
                    }
                ],
            }
        }
        await self.client.put(endpoint, body)
        display_prefix = f"{prefix}/{cidr}" if cidr else prefix
        return StaticRoute(prefix=display_prefix, next_hop=next_hop)

    async def delete_static_route(self, prefix: str, netmask: str) -> None:
        """Remove a static route from the target device."""

        dotted_mask, _ = self._normalize_netmask(netmask)
        endpoint = (
            "Cisco-IOS-XE-native:native/ip/route/ip-route-interface-forwarding-list="
            f"{prefix},{dotted_mask}"
        )
        await self.client.delete(endpoint)

    def _normalize_netmask(self, netmask: str) -> Tuple[str, str]:
        """Return dotted-decimal mask and CIDR length strings."""

        value = netmask.strip()
        if "/" in value:
            value = value.split("/", 1)[1]

        # Attempt CIDR integer first.
        try:
            cidr = int(value)
            if not 0 <= cidr <= 32:  # pragma: no cover - guardrail
                raise ValueError
            dotted = str(ipaddress.IPv4Network(f"0.0.0.0/{cidr}").netmask)
            return dotted, str(cidr)
        except ValueError:
            dotted = value
            try:
                network = ipaddress.IPv4Network(f"0.0.0.0/{dotted}")
                return dotted, str(network.prefixlen)
            except ValueError:
                return dotted, ""

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
        if payload is None:
            return []
        if isinstance(payload, dict):
            forwarding_entries = payload.get("ip-route-interface-forwarding-list")
            if forwarding_entries is not None:
                payload = forwarding_entries
            else:
                payload = [payload]
        if not isinstance(payload, list):
            return []
        routes: List[StaticRoute] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue

            prefix_value = entry.get("prefix") or entry.get("ip-prefix") or "unknown"
            mask_value = entry.get("mask") or entry.get("netmask")

            display_prefix = str(prefix_value)
            if mask_value:
                try:
                    cidr = ipaddress.IPv4Network(f"{prefix_value}/{mask_value}", strict=False).prefixlen
                    display_prefix = f"{prefix_value}/{cidr}"
                except ValueError:
                    display_prefix = f"{prefix_value}/{mask_value}"

            next_hop: object = entry.get("next-hop") or entry.get("fwd")
            if not next_hop:
                fwd_list = entry.get("fwd-list")
                if isinstance(fwd_list, list):
                    for candidate in fwd_list:
                        if isinstance(candidate, dict):
                            next_hop = candidate.get("fwd") or candidate.get("next-hop")
                            if next_hop:
                                break

            routes.append(StaticRoute(prefix=str(display_prefix), next_hop=str(next_hop or "unknown")))
        return routes
