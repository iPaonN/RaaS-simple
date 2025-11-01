"""Shared utilities for RESTCONF command groups."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import discord
from restconf.connection_manager import ConnectionManager
from utils.embeds import create_error_embed


class MissingConnectionError(RuntimeError):
    """Raised when a command requires a connection but none exists."""


@dataclass
class ConnectionCredentials:
    host: str
    username: str
    password: str


def resolve_connection_credentials(
    manager: ConnectionManager,
    host: Optional[str],
    username: Optional[str],
    password: Optional[str],
) -> ConnectionCredentials:
    """Return connection credentials, falling back to the stored connection."""
    if host and username and password:
        return ConnectionCredentials(host=host, username=username, password=password)

    connection = manager.get_connection()
    if connection is None:
        raise MissingConnectionError

    return ConnectionCredentials(
        host=host or connection.host,
        username=username or connection.username,
        password=password or connection.password,
    )


def build_no_connection_embed() -> discord.Embed:
    """Embed explaining that a RESTCONF connection is required."""
    return create_error_embed(
        title="❌ No Connection",
        description=(
            "No router connection found. Please either:\n\n"
            "• Use `/connect [host] [username] [password]` first, or\n"
            "• Provide host, username, and password parameters"
        ),
    )
