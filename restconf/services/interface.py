"""Interface-centric RESTCONF service operations."""
from __future__ import annotations

from typing import Dict, List

from restconf.errors import RestconfNotFoundError
from restconf.models import Interface, InterfaceAddress
from utils.logger import get_logger

from .base import RestconfDomainService

_logger = get_logger(__name__)


class InterfaceService(RestconfDomainService):
    """Operations that manage device interfaces via RESTCONF."""

    async def fetch_interfaces(self) -> List[Interface]:
        """Return all interfaces, preferring Cisco IOS-XE oper data."""
        try:
            payload = await self.client.get("Cisco-IOS-XE-interfaces-oper:interfaces")
            interfaces_data = payload.get("Cisco-IOS-XE-interfaces-oper:interfaces", {})
            if isinstance(interfaces_data, dict):
                interfaces = interfaces_data.get("interface", [])
                if interfaces:
                    _logger.debug("Parsed %d interface(s) using Cisco IOS-XE model", len(interfaces))
                    return [self._parse_cisco_xe_interface(raw) for raw in interfaces]
        except Exception as exc:  # pragma: no cover - fallback path
            _logger.warning("Cisco IOS-XE model failed, falling back to IETF: %s", exc)

        payload = await self.client.get("ietf-interfaces:interfaces")
        interfaces_data = payload.get("ietf-interfaces:interfaces", {})
        interfaces = interfaces_data.get("interface", []) if isinstance(interfaces_data, dict) else payload.get("interface", [])
        _logger.debug("Parsed %d interface(s) using IETF model", len(interfaces))
        return [self._parse_interface(raw) for raw in interfaces]

    async def fetch_interface(self, name: str) -> Interface:
        """Return interface details, trying vendor model before IETF."""
        try:
            payload = await self.client.get(f"Cisco-IOS-XE-interfaces-oper:interfaces/interface={name}")
            interface_payload = payload.get("Cisco-IOS-XE-interfaces-oper:interface")
            if interface_payload:
                return self._parse_cisco_xe_interface(interface_payload)
        except Exception:  # pragma: no cover - fallback path
            _logger.debug("Cisco IOS-XE interface lookup failed for %s", name)

        try:
            payload = await self.client.get(f"ietf-interfaces:interfaces/interface={name}")
        except RestconfNotFoundError as exc:
            raise RestconfNotFoundError(status=exc.status, message=f"Interface '{name}' not found", details=exc.details)

        interface_payload = payload.get("ietf-interfaces:interface")
        if not interface_payload:
            raise RestconfNotFoundError(status=404, message=f"Interface '{name}' not found")
        return self._parse_interface(interface_payload)

    async def update_interface_description(self, name: str, description: str) -> Interface:
        iface_type = self._get_interface_type(name)
        iface_number = self._get_interface_number(name)

        await self.client.patch(
            f"Cisco-IOS-XE-native:native/interface/{iface_type}={iface_number}",
            data={
                f"Cisco-IOS-XE-native:{iface_type}": {
                    "name": iface_number,
                    "description": description,
                }
            },
        )
        _logger.info("Updated description on interface %s", name)
        return await self.fetch_interface(name)

    async def update_interface_state(self, name: str, enabled: bool) -> Interface:
        """Enable or disable an interface using Cisco IOS-XE native model.
        
        Args:
            name: Interface name (e.g., GigabitEthernet1)
            enabled: True to enable (no shutdown), False to disable (shutdown)
        
        Returns:
            Updated Interface object
        """
        iface_type = self._get_interface_type(name)
        iface_number = self._get_interface_number(name)

        if enabled:
            # To enable: DELETE the shutdown configuration (no shutdown)
            try:
                await self.client.delete(
                    f"Cisco-IOS-XE-native:native/interface/{iface_type}={iface_number}/shutdown"
                )
            except RestconfNotFoundError:
                # If shutdown doesn't exist, interface is already enabled
                _logger.info("Interface %s is already enabled (no shutdown config found)", name)
        else:
            # To disable: PATCH with shutdown configuration
            data = {
                f"Cisco-IOS-XE-native:{iface_type}": {
                    "name": iface_number,
                    "shutdown": [None]
                }
            }
            await self.client.patch(
                f"Cisco-IOS-XE-native:native/interface/{iface_type}={iface_number}",
                data=data,
            )
        
        _logger.info("Set interface %s state to %s", name, "enabled" if enabled else "disabled")
        return await self.fetch_interface(name)

    async def update_interface_ip(self, name: str, ip: str, netmask: str) -> Interface:
        iface_type = self._get_interface_type(name)
        iface_number = self._get_interface_number(name)

        await self.client.patch(
            f"Cisco-IOS-XE-native:native/interface/{iface_type}={iface_number}",
            data={
                f"Cisco-IOS-XE-native:{iface_type}": {
                    "name": iface_number,
                    "ip": {
                        "address": {
                            "primary": {
                                "address": ip,
                                "mask": netmask,
                            }
                        }
                    },
                }
            },
        )
        _logger.info("Updated IP %s/%s on interface %s", ip, netmask, name)
        return await self.fetch_interface(name)

    # ------------------------------------------------------------------
    # Parsers and helpers
    # ------------------------------------------------------------------
    def _get_interface_type(self, interface_name: str) -> str:
        import re

        match = re.match(r"^([A-Za-z-]+)", interface_name)
        if match:
            return match.group(1)
        return "GigabitEthernet"

    def _get_interface_number(self, interface_name: str) -> str:
        import re

        match = re.match(r"^[A-Za-z-]+(.+)", interface_name)
        if match:
            return match.group(1)
        return "0"

    def _parse_cisco_xe_interface(self, payload: Dict[str, object]) -> Interface:
        name = str(payload.get("name", "unknown"))
        enabled = payload.get("admin-status") == "if-state-up" if "admin-status" in payload else bool(payload.get("enabled", False))
        interface_type = str(payload.get("interface-type", "unknown"))
        description = str(payload.get("description")) if payload.get("description") else None

        addresses = []
        ipv4_data = payload.get("ipv4", {}) if isinstance(payload.get("ipv4"), dict) else {}
        ipv4_address = ipv4_data.get("address")
        ipv4_netmask = ipv4_data.get("netmask")
        if ipv4_address and ipv4_netmask:
            addresses.append(InterfaceAddress(ip=str(ipv4_address), netmask=str(ipv4_netmask)))

        return Interface(
            name=name,
            enabled=enabled,
            type=interface_type,
            description=description,
            ipv4_addresses=addresses,
        )

    def _parse_interface(self, payload: Dict[str, object]) -> Interface:
        addresses_payload = (
            payload.get("ietf-ip:ipv4", {}) if isinstance(payload.get("ietf-ip:ipv4"), dict) else {}
        ).get("address", [])

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
