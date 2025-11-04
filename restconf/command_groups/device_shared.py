"""Shared helpers for RESTCONF device command builders."""
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
from restconf.errors import RestconfError
from restconf.presenters import render_restconf_error
from restconf.service import RestconfService

ServiceBuilder = Callable[[str, str, str], RestconfService]


@dataclass
class DeviceCommandContext:
    """Resolved connection credentials and service instance for a device command."""

    credentials: ConnectionCredentials
    service: RestconfService


async def resolve_device_context(
    interaction: discord.Interaction,
    service_builder: ServiceBuilder,
    connection_manager: ConnectionManager,
    host: Optional[str],
    username: Optional[str],
    password: Optional[str],
) -> Optional[DeviceCommandContext]:
    """Resolve credentials from interaction parameters or stored connection."""

    try:
        credentials = resolve_connection_credentials(connection_manager, host, username, password)
    except MissingConnectionError:
        await interaction.followup.send(embed=build_no_connection_embed(), ephemeral=True)
        return None

    service = service_builder(credentials.host, credentials.username, credentials.password)
    return DeviceCommandContext(credentials=credentials, service=service)


async def send_restconf_failure(interaction: discord.Interaction, exc: RestconfError) -> None:
    """Send a standardized RESTCONF failure embed."""

    await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
