"""Domain models representing RESTCONF resources."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass(slots=True)
class InterfaceAddress:
    """IPv4 address assigned to an interface."""

    ip: str
    netmask: str


@dataclass(slots=True)
class Interface:
    """Representation of a network interface."""

    name: str
    enabled: bool
    type: str
    description: Optional[str]
    ipv4_addresses: List[InterfaceAddress]

    @property
    def status_emoji(self) -> str:
        return "✅" if self.enabled else "❌"


@dataclass(slots=True)
class Hostname:
    """Device hostname."""

    value: str


@dataclass(slots=True)
class StaticRoute:
    """Static route entry."""

    prefix: str
    next_hop: str


@dataclass(slots=True)
class RoutingTable:
    """Routing table with static routes."""

    static_routes: List[StaticRoute]

    @classmethod
    def from_routes(cls, routes: Iterable[StaticRoute]) -> "RoutingTable":
        return cls(static_routes=list(routes))
