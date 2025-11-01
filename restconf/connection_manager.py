"""Connection manager for maintaining router connection state."""
from typing import Optional
from dataclasses import dataclass


@dataclass
class RouterConnection:
    """Represents a router connection."""
    host: str
    username: str
    password: str


class ConnectionManager:
    """Manages the current router connection state."""
    
    def __init__(self):
        self._connection: Optional[RouterConnection] = None
    
    def set_connection(self, host: str, username: str, password: str) -> None:
        """Set the current router connection."""
        self._connection = RouterConnection(
            host=host,
            username=username,
            password=password
        )
    
    def get_connection(self) -> Optional[RouterConnection]:
        """Get the current router connection."""
        return self._connection
    
    def clear_connection(self) -> None:
        """Clear the current router connection."""
        self._connection = None
    
    def is_connected(self) -> bool:
        """Check if a router connection is active."""
        return self._connection is not None
    
    def get_host(self) -> Optional[str]:
        """Get the current router host/IP."""
        if self._connection:
            return self._connection.host
        return None
