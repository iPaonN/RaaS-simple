"""Slash command registrations for routing operations."""
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
from restconf.presenters import (
    render_restconf_error,
    render_static_routes,
)
from restconf.service import RestconfService
from utils.embeds import create_error_embed, create_success_embed

ServiceBuilder = Callable[[str, str, str], RestconfService]


async def _resolve_service_context(
    interaction: discord.Interaction,
    service_builder: ServiceBuilder,
    connection_manager: ConnectionManager,
    host: Optional[str],
    username: Optional[str],
    password: Optional[str],
) -> tuple[RestconfService, str] | None:
    """Resolve credentials and build a service or notify the user when missing."""

    try:
        creds = resolve_connection_credentials(connection_manager, host, username, password)
    except MissingConnectionError:
        await interaction.followup.send(embed=build_no_connection_embed(), ephemeral=True)
        return None

    service = service_builder(creds.host, creds.username, creds.password)
    return service, creds.host


async def _send_restconf_error(
    interaction: discord.Interaction,
    error: RestconfError,
) -> None:
    await interaction.followup.send(embed=render_restconf_error(str(error)), ephemeral=True)


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

        context = await _resolve_service_context(
            interaction,
            service_builder,
            connection_manager,
            host,
            username,
            password,
        )
        if context is None:
            return

        service, router_host = context
        try:
            routes = await service.routing.fetch_static_routes()
        except RestconfError as exc:
            await _send_restconf_error(interaction, exc)
            return
        await interaction.followup.send(embed=render_static_routes(router_host, routes))

    return command


def _build_add_static_route(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="add-static-route", description="Add a static route")
    @app_commands.describe(
        prefix="Network prefix (e.g., 192.168.10.0)",
        netmask="Subnet mask in CIDR (e.g., 24) or dotted decimal (e.g., 255.255.255.0)",
        next_hop="Next hop IP address (e.g., 10.0.0.1)",
        host="Router IP address or hostname (optional if connected)",
        username="RESTCONF username (optional if connected)",
        password="RESTCONF password (optional if connected)",
    )
    async def command(
        interaction: discord.Interaction,
        prefix: str,
        netmask: str,
        next_hop: str,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(thinking=True)

        context = await _resolve_service_context(
            interaction,
            service_builder,
            connection_manager,
            host,
            username,
            password,
        )
        if context is None:
            return

        service, router_host = context
        try:
            route = await service.routing.add_static_route(prefix, netmask, next_hop)
            embed = create_success_embed(
                title="✅ Static Route Added",
                description=f"Successfully added static route on **{router_host}**"
            )
            embed.add_field(
                name="📍 Network",
                value=f"`{route.prefix}`",
                inline=False
            )
            embed.add_field(
                name="➜ Next Hop",
                value=f"`{route.next_hop}`",
                inline=False
            )
            await interaction.followup.send(embed=embed)
        except RestconfError as exc:
            await _send_restconf_error(interaction, exc)

    return command


def _build_delete_static_route(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="delete-static-route", description="Delete a static route")
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

        context = await _resolve_service_context(
            interaction,
            service_builder,
            connection_manager,
            host,
            username,
            password,
        )
        if context is None:
            return

        service, router_host = context

        try:
            routes = await service.routing.fetch_static_routes()
        except RestconfError as exc:
            await _send_restconf_error(interaction, exc)
            return

        if not routes:
            embed = create_error_embed(
                title="❌ No Routes Found",
                description=f"No static routes found on **{router_host}**"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="🗑️ Delete Static Route",
            description=f"เลือก route ที่ต้องการลบจาก **{router_host}**",
            color=discord.Color.blue(),
        )
        view = _RouteSelectView(router_host, service, routes)
        await interaction.followup.send(embed=embed, view=view)

    return command


class RoutingCommandGroup(CommandGroup):
    def __init__(self, service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_get_static_routes(service_builder, connection_manager),
            _build_add_static_route(service_builder, connection_manager),
            _build_delete_static_route(service_builder, connection_manager),
        ]
        super().__init__(commands)


class _RouteSelectView(discord.ui.View):
    def __init__(
        self,
        router_host: str,
        service: RestconfService,
        routes: Sequence,
    ) -> None:
        super().__init__(timeout=60.0)
        routes_list = list(routes)
        route_options = [
            discord.SelectOption(
                label=f"{route.prefix} → {route.next_hop}",
                value=str(route.prefix),
                description=f"Next hop: {route.next_hop}",
            )
            for route in routes_list[:25]
        ]
        self.add_item(
            _RouteSelect(router_host=router_host, service=service, routes=routes_list, options=route_options)
        )


class _RouteSelect(discord.ui.Select):
    def __init__(
        self,
        *,
        router_host: str,
        service: RestconfService,
        routes: Sequence,
        options: list[discord.SelectOption],
    ) -> None:
        super().__init__(
            placeholder="เลือก static route ที่ต้องการลบ",
            min_values=1,
            max_values=1,
            options=options,
        )
        self._router_host = router_host
        self._service = service
        self._routes = list(routes)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        selected_prefix = self.values[0]
        selected_route = next((route for route in self._routes if str(route.prefix) == selected_prefix), None)

        if selected_route is None:
            await interaction.followup.send(
                embed=create_error_embed(title="❌ Error", description="Route not found"),
                ephemeral=True,
            )
            return

        prefix_parts = str(selected_route.prefix).split("/")
        prefix_addr = prefix_parts[0]
        netmask = prefix_parts[1] if len(prefix_parts) > 1 else "32"

        try:
            await self._service.routing.delete_static_route(prefix_addr, netmask)
        except RestconfError as exc:
            await _send_restconf_error(interaction, exc)
            return

        embed = create_success_embed(
            title="✅ Static Route Deleted",
            description=f"Successfully deleted static route on **{self._router_host}**",
        )
        embed.add_field(name="📍 Network", value=f"`{selected_route.prefix}`", inline=False)
        embed.add_field(name="➜ Next Hop", value=f"`{selected_route.next_hop}`", inline=False)
        await interaction.followup.send(embed=embed)

        if self.view:
            self.view.stop()
