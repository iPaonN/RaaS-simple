"""Slash command registrations for device configuration."""
from __future__ import annotations

from typing import Callable, Optional, Sequence

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.command_groups.utils import (
    MissingConnectionError,
    build_no_connection_embed,
    resolve_connection_credentials,
)
from restconf.connection_manager import ConnectionManager
from restconf.errors import RestconfError
from restconf.presenters import render_hostname, render_restconf_error
from restconf.service import RestconfService

ServiceBuilder = Callable[[str, str, str], RestconfService]


def _build_get_hostname(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="get-hostname", description="Get router hostname")
    @app_commands.describe(
        host="Router IP address or hostname (optional if connected)",
        username="RESTCONF username (optional if connected)",
        password="RESTCONF password (optional if connected)",
    )
    async def command(
        interaction: discord.Interaction,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        
        # Use stored connection if no parameters provided
        try:
            creds = resolve_connection_credentials(connection_manager, host, username, password)
        except MissingConnectionError:
            await interaction.followup.send(embed=build_no_connection_embed(), ephemeral=True)
            return

        service = service_builder(creds.host, creds.username, creds.password)
        try:
            hostname = await service.device.fetch_hostname()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_hostname(creds.host, hostname))

    return command


def _build_set_hostname(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="set-hostname", description="Set router hostname")
    @app_commands.describe(
        hostname="New hostname",
        host="Router IP address or hostname (optional if connected)",
        username="RESTCONF username (optional if connected)",
        password="RESTCONF password (optional if connected)",
    )
    async def command(
        interaction: discord.Interaction,
        hostname: str,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        
        # Use stored connection if no parameters provided
        try:
            creds = resolve_connection_credentials(connection_manager, host, username, password)
        except MissingConnectionError:
            await interaction.followup.send(embed=build_no_connection_embed(), ephemeral=True)
            return

        service = service_builder(creds.host, creds.username, creds.password)
        try:
            hostname_model = await service.device.update_hostname(hostname)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_hostname(creds.host, hostname_model))

    return command


class DeviceCommandGroup(CommandGroup):
    def __init__(self, service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_get_hostname(service_builder, connection_manager),
            _build_set_hostname(service_builder, connection_manager),
        ]
        super().__init__(commands)