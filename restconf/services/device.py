"""Device-level RESTCONF operations."""
from __future__ import annotations

from restconf.errors import RestconfHTTPError
from restconf.models import Hostname
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
