"""Slash command registrations for routing operations."""
from __future__ import annotations

from typing import Callable, Sequence

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.errors import RestconfError
from restconf.presenters import (
    render_restconf_error,
    render_routing_table,
    render_static_routes,
)
from restconf.service import RestconfService

ServiceBuilder = Callable[[str, str, str], RestconfService]


def _build_get_routing_table(service_builder: ServiceBuilder) -> app_commands.Command:
    @app_commands.command(name="get-routing-table", description="Get routing table information")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
    )
    async def command(
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
    ) -> None:
        await interaction.response.defer(thinking=True)
        service = service_builder(host, username, password)
        try:
            table = await service.fetch_routing_table()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_routing_table(host, table))

    return command


def _build_get_static_routes(service_builder: ServiceBuilder) -> app_commands.Command:
    @app_commands.command(name="get-static-routes", description="Get static routes")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
    )
    async def command(
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
    ) -> None:
        await interaction.response.defer(thinking=True)
        service = service_builder(host, username, password)
        try:
            routes = await service.fetch_static_routes()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_static_routes(host, routes))

    return command


class RoutingCommandGroup(CommandGroup):
    def __init__(self, service_builder: ServiceBuilder) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_get_routing_table(service_builder),
            _build_get_static_routes(service_builder),
        ]
        super().__init__(commands)
