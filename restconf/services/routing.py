"""Routing-related RESTCONF operations."""
from __future__ import annotations

from typing import Dict, List

from restconf.errors import RestconfNotFoundError
from restconf.models import StaticRoute
from utils.logger import get_logger

from .base import RestconfDomainService

_logger = get_logger(__name__)


class RoutingService(RestconfDomainService):
    """Operations focused on routing datasets."""

    async def fetch_static_routes(self) -> List[StaticRoute]:
        """Fetch static routes using Cisco IOS-XE native model."""
        try:
            payload = await self.client.get("Cisco-IOS-XE-native:native/ip/route")
            routes_payload = payload.get("Cisco-IOS-XE-native:route", {})
            
            # Handle both dict and list formats
            if isinstance(routes_payload, dict):
                route_list = routes_payload.get("ip-route-interface-forwarding-list", [])
            else:
                route_list = routes_payload
            
            routes = self._parse_cisco_static_routes(route_list)
            _logger.info("Found %d static route(s)", len(routes))
            return routes
        except RestconfNotFoundError:
            _logger.info("No static routes configured")
            return []
        except Exception as e:
            _logger.error("Failed to fetch static routes: %s", e)
            return []

    async def add_static_route(self, prefix: str, netmask: str, next_hop: str) -> StaticRoute:
        """Add a static route using Cisco IOS-XE native model."""
        # Convert CIDR to dotted decimal if needed
        mask = netmask if '.' in netmask else self._cidr_to_netmask(int(netmask))
        prefix_length = self._netmask_to_cidr(mask) if '.' in mask else int(netmask)
        destination_prefix = f"{prefix}/{prefix_length}"
        
        data = {
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
        
        await self.client.put(
            f"Cisco-IOS-XE-native:native/ip/route/ip-route-interface-forwarding-list={prefix},{mask}",
            data=data
        )
        _logger.info("Added static route %s/%s via %s", prefix, mask, next_hop)
        return StaticRoute(prefix=destination_prefix, next_hop=next_hop)

    async def delete_static_route(self, prefix: str, netmask: str) -> None:
        """Delete a static route using Cisco IOS-XE native model."""
        mask = netmask if '.' in netmask else self._cidr_to_netmask(int(netmask))
        
        await self.client.delete(
            f"Cisco-IOS-XE-native:native/ip/route/ip-route-interface-forwarding-list={prefix},{mask}"
        )
        _logger.info("Deleted static route %s/%s", prefix, mask)

    def _parse_cisco_static_routes(self, routes_payload: object) -> List[StaticRoute]:
        """Parse static routes from Cisco IOS-XE native model."""
        if isinstance(routes_payload, dict):
            routes_payload = [routes_payload]
        if not isinstance(routes_payload, list):
            return []
        
        routes: List[StaticRoute] = []
        for entry in routes_payload:
            if not isinstance(entry, dict):
                continue
            
            prefix = entry.get("prefix")
            mask = entry.get("mask")
            
            if not prefix:
                continue
            
            network = f"{prefix}/{mask}" if mask else prefix
            
            # Get next-hop from fwd-list
            next_hop = None
            fwd_list = entry.get("fwd-list", [])
            
            if isinstance(fwd_list, list) and fwd_list:
                first_fwd = fwd_list[0] if isinstance(fwd_list[0], dict) else {}
                next_hop = first_fwd.get("fwd")
            elif isinstance(fwd_list, dict):
                next_hop = fwd_list.get("fwd")
            
            if not next_hop:
                interface = entry.get("interface")
                if interface:
                    next_hop = f"via {interface}"
            
            if not next_hop:
                next_hop = "unknown"
            
            routes.append(StaticRoute(prefix=network, next_hop=str(next_hop)))
        
        return routes

    def _netmask_to_cidr(self, netmask: str) -> int:
        """Convert dotted decimal netmask to CIDR prefix length."""
        return sum([bin(int(x)).count('1') for x in netmask.split('.')])

    def _cidr_to_netmask(self, prefix_length: int) -> str:
        """Convert CIDR prefix length to dotted decimal netmask."""
        mask = (0xffffffff >> (32 - prefix_length)) << (32 - prefix_length)
        return f"{(mask >> 24) & 0xff}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"

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
