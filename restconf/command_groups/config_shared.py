"""Shared helpers for RESTCONF configuration command builders."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import discord

from restconf.command_groups.utils import (
    ConnectionCredentials,
    MissingConnectionError,
    build_no_connection_embed,
    resolve_connection_credentials,
)
from restconf.connection_manager import ConnectionManager
from netmiko_client import ConfigService

ConfigServiceBuilder = Callable[[str, str, str], ConfigService]


@dataclass
class ConfigCommandContext:
    """Result of resolving credentials and instantiating a config service."""

    credentials: ConnectionCredentials
    service: ConfigService


async def resolve_config_context(
    interaction: discord.Interaction,
    connection_manager: ConnectionManager,
    service_builder: ConfigServiceBuilder,
    host: Optional[str],
    username: Optional[str],
    password: Optional[str],
) -> Optional[ConfigCommandContext]:
    """Resolve connection credentials and construct a config service."""

    try:
        credentials = resolve_connection_credentials(connection_manager, host, username, password)
    except MissingConnectionError:
        await interaction.followup.send(embed=build_no_connection_embed(), ephemeral=True)
        return None

    service = service_builder(credentials.host, credentials.username, credentials.password)
    return ConfigCommandContext(credentials=credentials, service=service)
