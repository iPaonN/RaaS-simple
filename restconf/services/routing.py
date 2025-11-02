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
        payload = await self._client.get("Cisco-IOS-XE-native:native/ip/route")
        routes_payload = payload.get("Cisco-IOS-XE-native:route", {})
        # Handle ip-route-interface-forwarding-list structure
        route_list = routes_payload.get("ip-route-interface-forwarding-list", [])
        return self._parse_static_routes(route_list)

    async def add_static_route(self, prefix: str, netmask: str, next_hop: str) -> StaticRoute:
        """Add a static route to the router.
        
        Args:
            prefix: Network prefix (e.g., "192.168.10.0")
            netmask: Subnet mask in CIDR (e.g., "24") or dotted decimal (e.g., "255.255.255.0")
            next_hop: Next hop IP address (e.g., "10.0.0.1")
        
        Returns:
            StaticRoute object representing the added route
        """
        # Convert netmask to dotted decimal if it's CIDR
        mask = self._cidr_to_netmask(netmask) if netmask.isdigit() else netmask
        
        # Use POST to add to the list
        payload = {
            "Cisco-IOS-XE-native:ip-route-interface-forwarding-list": {
                "prefix": prefix,
                "mask": mask,
                "fwd-list": [
                    {
                        "fwd": next_hop
                    }
                ]
            }
        }
        
        # POST to the route collection
        await self._client.post(
            "Cisco-IOS-XE-native:native/ip/route",
            payload
        )
        
        # Return the created route in CIDR format
        cidr = self._netmask_to_cidr(mask)
        return StaticRoute(prefix=f"{prefix}/{cidr}", next_hop=next_hop)

    async def delete_static_route(self, prefix: str, netmask: str) -> None:
        """Delete a static route from the router.
        
        Args:
            prefix: Network prefix (e.g., "192.168.10.0")
            netmask: Subnet mask in CIDR (e.g., "24") or dotted decimal (e.g., "255.255.255.0")
        """
        # Convert netmask to dotted decimal if it's CIDR
        mask = self._cidr_to_netmask(netmask) if netmask.isdigit() else netmask
        
        # DELETE the route
        await self._client.delete(
            f"Cisco-IOS-XE-native:native/ip/route/ip-route-interface-forwarding-list={prefix},{mask}"
        )

    def _cidr_to_netmask(self, cidr: str) -> str:
        """Convert CIDR notation to dotted decimal netmask."""
        cidr_int = int(cidr)
        mask = (0xffffffff >> (32 - cidr_int)) << (32 - cidr_int)
        return f"{(mask >> 24) & 0xff}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"

    def _netmask_to_cidr(self, netmask: str) -> int:
        """Convert dotted decimal netmask to CIDR notation."""
        return sum([bin(int(x)).count('1') for x in netmask.split('.')])

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
            
            # Get prefix and mask
            prefix = entry.get("prefix", "unknown")
            mask = entry.get("mask", "255.255.255.255")
            
            # Convert to CIDR format
            if prefix != "unknown" and mask != "255.255.255.255":
                cidr = self._netmask_to_cidr(mask)
                prefix_cidr = f"{prefix}/{cidr}"
            else:
                prefix_cidr = prefix
            
            # Get next hop from fwd-list
            fwd_list = entry.get("fwd-list", [])
            next_hop = "unknown"
            if isinstance(fwd_list, list) and len(fwd_list) > 0:
                first_fwd = fwd_list[0]
                if isinstance(first_fwd, dict):
                    next_hop = first_fwd.get("fwd", "unknown")
            
            routes.append(StaticRoute(prefix=prefix_cidr, next_hop=next_hop))
        return routes
