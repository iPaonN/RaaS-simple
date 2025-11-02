"""Device-level RESTCONF operations."""
from __future__ import annotations

from typing import List

from restconf.errors import RestconfHTTPError, RestconfNotFoundError
from restconf.models import Banner, DeviceConfig, DomainName, Hostname, NameServerList
from utils.logger import get_logger

from .base import RestconfDomainService

_logger = get_logger(__name__)


class DeviceService(RestconfDomainService):
    """Operations for retrieving and updating device metadata."""

    async def fetch_hostname(self) -> Hostname:
        payload = await self.client.get("Cisco-IOS-XE-native:native/hostname")
        value = payload.get("Cisco-IOS-XE-native:hostname")
        if not value:
            raise RestconfHTTPError(status=500, message="Hostname missing in payload")
        return Hostname(value=value)

    async def update_hostname(self, hostname: str) -> Hostname:
        await self.client.patch(
            "Cisco-IOS-XE-native:native/hostname",
            data={"Cisco-IOS-XE-native:hostname": hostname},
        )
        _logger.info("Updated hostname to %s", hostname)
        return Hostname(value=hostname)

    # ------------------------------------------------------------------
    # Configuration retrieval
    # ------------------------------------------------------------------
    async def fetch_running_config(self) -> DeviceConfig:
        """Return the device running configuration."""
        try:
            payload = await self.client.get("Cisco-IOS-XE-native:native")
        except RestconfHTTPError:
            # Fall back to the IETF interface model
            payload = await self.client.get("ietf-interfaces:interfaces")

        import json

        config_content = json.dumps(payload, indent=2)
        return DeviceConfig(config_type="running", content=config_content, size=len(config_content))

    async def fetch_startup_config(self) -> DeviceConfig:
        """Return the startup configuration if available."""
        try:
            payload = await self.client.get("Cisco-IOS-XE-native:native")
        except RestconfHTTPError as exc:
            raise RestconfHTTPError(status=exc.status, message="Unable to fetch startup config", details=exc.details)

        import json

        config_content = json.dumps(payload, indent=2)
        return DeviceConfig(
            config_type="startup",
            content=(
                "Startup config may not be available via RESTCONF.\n"
                "Showing running config instead:\n\n"
                f"{config_content}"
            ),
            size=len(config_content),
        )

    # ------------------------------------------------------------------
    # Banner operations
    # ------------------------------------------------------------------
    async def fetch_banner_motd(self) -> Banner:
        try:
            payload = await self.client.get("Cisco-IOS-XE-native:native/banner/motd")
        except RestconfNotFoundError:
            return Banner(banner_type="motd", message="No MOTD banner configured")

        motd_data = payload.get("Cisco-IOS-XE-native:motd", {})
        banner_text = ""
        if isinstance(motd_data, dict):
            banner_text = str(motd_data.get("banner", ""))
        return Banner(banner_type="motd", message=banner_text or "No MOTD banner configured")

    async def update_banner_motd(self, message: str) -> Banner:
        await self.client.patch(
            "Cisco-IOS-XE-native:native/banner",
            data={
                "Cisco-IOS-XE-native:banner": {
                    "motd": {
                        "banner": message,
                    }
                }
            },
        )
        _logger.info("Updated MOTD banner")
        return Banner(banner_type="motd", message=message)

    # ------------------------------------------------------------------
    # Domain name operations
    # ------------------------------------------------------------------
    async def fetch_domain_name(self) -> DomainName:
        try:
            payload = await self.client.get("Cisco-IOS-XE-native:native/ip/domain/name")
        except RestconfNotFoundError:
            return DomainName(value="No domain name configured")

        domain_value = payload.get("Cisco-IOS-XE-native:name", "")
        return DomainName(value=domain_value or "No domain name configured")

    async def update_domain_name(self, domain: str) -> DomainName:
        await self.client.put(
            "Cisco-IOS-XE-native:native/ip/domain/name",
            data={"Cisco-IOS-XE-native:name": domain},
        )
        _logger.info("Updated domain name to %s", domain)
        return DomainName(value=domain)

    # ------------------------------------------------------------------
    # Name server operations
    # ------------------------------------------------------------------
    async def fetch_name_servers(self) -> NameServerList:
        try:
            payload = await self.client.get("Cisco-IOS-XE-native:native/ip/name-server")
        except RestconfNotFoundError:
            return NameServerList(servers=[])

        servers_data = payload.get("Cisco-IOS-XE-native:name-server", {})
        servers: List[str] = []

        if isinstance(servers_data, dict):
            for vrf_servers in servers_data.values():
                servers.extend(self._extract_servers(vrf_servers))
        else:
            servers.extend(self._extract_servers(servers_data))

        _logger.info("Resolved %d DNS server(s)", len(servers))
        return NameServerList(servers=servers)

    def _extract_servers(self, payload: object) -> List[str]:
        servers: List[str] = []
        if isinstance(payload, list):
            for entry in payload:
                if isinstance(entry, str):
                    servers.append(entry)
                elif isinstance(entry, dict):
                    for key in ("ip", "name", "address", "server"):
                        if key in entry:
                            servers.append(str(entry[key]))
                            break
        elif isinstance(payload, str):
            servers.append(payload)
        elif isinstance(payload, dict):
            for key in ("ip", "name", "address", "server"):
                if key in payload:
                    servers.append(str(payload[key]))
                    break
        return servers

    # ------------------------------------------------------------------
    # Save configuration
    # ------------------------------------------------------------------
    async def save_config(self) -> bool:
        try:
            await self.client.post_operation("cisco-ia:save-config", data={})
        except Exception as exc:  # pragma: no cover - device-specific failures
            _logger.error("Failed to save configuration: %s", exc)
            raise RestconfHTTPError(status=500, message="Unable to save configuration", details=str(exc)) from exc

        _logger.info("Configuration saved successfully")
        return True
