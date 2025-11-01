"""Services for managing RESTCONF session lifecycle."""
from __future__ import annotations

from dataclasses import dataclass

from restconf.client import RestconfClient
from restconf.connection_manager import ConnectionManager, RouterConnection
from restconf.errors import RestconfConnectionError, RestconfHTTPError
from utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass
class ConnectionResult:
    host: str
    hostname: str


class ConnectionService:
    """High-level operations for establishing and clearing connections."""

    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager

    async def connect(self, host: str, username: str, password: str) -> ConnectionResult:
        """Validate credentials and store the connection."""
        client = RestconfClient(host=host, username=username, password=password)

        try:
            payload = await client.get("Cisco-IOS-XE-native:native/hostname")
        except (RestconfConnectionError, RestconfHTTPError):
            raise
        except Exception as exc:  # pragma: no cover - unexpected
            raise RestconfConnectionError(str(exc), host=host) from exc

        hostname_value = payload.get("Cisco-IOS-XE-native:hostname") or "unknown"
        self._manager.set_connection(host, username, password)
        _logger.info("Stored RESTCONF connection for %s", host)
        return ConnectionResult(host=host, hostname=hostname_value)

    def disconnect(self) -> None:
        """Clear the stored connection if present."""
        if self._manager.is_connected():
            host = self._manager.get_host()
            self._manager.clear_connection()
            _logger.info("Cleared RESTCONF connection for %s", host)

    def current_host(self) -> str | None:
        connection = self._manager.get_connection()
        return connection.host if connection else None

    def get_connection(self) -> RouterConnection | None:
        return self._manager.get_connection()