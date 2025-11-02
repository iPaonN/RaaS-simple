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


@dataclass(slots=True)
class DeviceConfig:
    """Device configuration (running or startup)."""

    config_type: str  # "running" or "startup"
    content: str  # Configuration content
    size: int  # Size in bytes

    @property
    def preview(self) -> str:
        """Get first 20 lines as preview."""
        lines = self.content.split('\n')
        if len(lines) > 20:
            return '\n'.join(lines[:20]) + '\n...(truncated)'
        return self.content


@dataclass(slots=True)
class Banner:
    """Device banner (MOTD or Login)."""

    banner_type: str  # "motd" or "login"
    message: str  # Banner message content

    @property
    def is_configured(self) -> bool:
        """Check if banner has content."""
        return bool(self.message and self.message.strip())


@dataclass(slots=True)
class DomainName:
    """Device domain name."""

    value: str  # Domain name (e.g., "example.com")

    @property
    def is_configured(self) -> bool:
        """Check if domain name is configured."""
        return bool(self.value and self.value.strip())


@dataclass(slots=True)
class NameServerList:
    """List of DNS name servers."""

    servers: List[str]  # List of DNS server IP addresses

    @property
    def count(self) -> int:
        """Get number of configured servers."""
        return len(self.servers)

    @property
    def is_configured(self) -> bool:
        """Check if any name servers are configured."""
        return len(self.servers) > 0
