"""Slash command registrations for routing operations."""
from __future__ import annotations

from typing import Callable, Optional, Sequence

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.connection_manager import ConnectionManager
from restconf.errors import RestconfError
from restconf.presenters import (
    render_restconf_error,
    render_routing_table,
    render_static_routes,
)
from restconf.service import RestconfService
from utils.embeds import create_error_embed

ServiceBuilder = Callable[[str, str, str], RestconfService]


def _build_get_routing_table(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="get-routing-table", description="Get routing table information")
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
            table = await service.fetch_routing_table()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_routing_table(host, table))

    return command


def _build_get_static_routes(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="get-static-routes", description="Get static routes")
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
            routes = await service.fetch_static_routes()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_static_routes(host, routes))

    return command


class RoutingCommandGroup(CommandGroup):
    def __init__(self, service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_get_routing_table(service_builder, connection_manager),
            _build_get_static_routes(service_builder, connection_manager),
        ]
        super().__init__(commands)
