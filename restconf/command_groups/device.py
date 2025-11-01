"""Slash command registrations for device configuration."""
from __future__ import annotations

from typing import Callable, Optional, Sequence

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.connection_manager import ConnectionManager
from restconf.errors import RestconfError
from restconf.presenters import render_hostname, render_restconf_error
from restconf.service import RestconfService
from utils.embeds import create_error_embed

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
        if host is None or username is None or password is None:
            conn = connection_manager.get_connection()
            if conn is None:
                embed = create_error_embed(
                    title="❌ No Connection",
                    description="No router connection found. Please either:\n\n"
                                "• Use `/connect [host] [username] [password]` first, or\n"
                                "• Provide host, username, and password parameters"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            host = conn.host
            username = conn.username
            password = conn.password
        
        service = service_builder(host, username, password)
        try:
            hostname = await service.fetch_hostname()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_hostname(host, hostname))

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
        if host is None or username is None or password is None:
            conn = connection_manager.get_connection()
            if conn is None:
                embed = create_error_embed(
                    title="❌ No Connection",
                    description="No router connection found. Please either:\n\n"
                                "• Use `/connect [host] [username] [password]` first, or\n"
                                "• Provide host, username, and password parameters"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            host = conn.host
            username = conn.username
            password = conn.password
        
        service = service_builder(host, username, password)
        try:
            hostname_model = await service.update_hostname(hostname)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_hostname(host, hostname_model))

    return command


class DeviceCommandGroup(CommandGroup):
    def __init__(self, service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_get_hostname(service_builder, connection_manager),
            _build_set_hostname(service_builder, connection_manager),
        ]
        super().__init__(commands)