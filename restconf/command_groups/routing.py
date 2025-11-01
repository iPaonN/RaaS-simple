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
        try:
            creds = resolve_connection_credentials(connection_manager, host, username, password)
        except MissingConnectionError:
            await interaction.followup.send(embed=build_no_connection_embed(), ephemeral=True)
            return

        service = service_builder(creds.host, creds.username, creds.password)
        try:
            routes = await service.routing.fetch_static_routes()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_static_routes(creds.host, routes))

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
        
        try:
            creds = resolve_connection_credentials(connection_manager, host, username, password)
        except MissingConnectionError:
            await interaction.followup.send(embed=build_no_connection_embed(), ephemeral=True)
            return
        
        service = service_builder(creds.host, creds.username, creds.password)
        try:
            route = await service.routing.add_static_route(prefix, netmask, next_hop)
            embed = create_success_embed(
                title="✅ Static Route Added",
                description=f"Successfully added static route on **{creds.host}**"
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
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)

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
        
        try:
            creds = resolve_connection_credentials(connection_manager, host, username, password)
        except MissingConnectionError:
            await interaction.followup.send(embed=build_no_connection_embed(), ephemeral=True)
            return
        
        service = service_builder(creds.host, creds.username, creds.password)
        
        # Fetch existing routes
        try:
            routes = await service.routing.fetch_static_routes()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        
        if not routes:
            embed = create_error_embed(
                title="❌ No Routes Found",
                description=f"No static routes found on **{creds.host}**"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Create select menu view
        class RouteSelectView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60.0)
                
            @discord.ui.select(
                placeholder="เลือก static route ที่ต้องการลบ",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(
                        label=f"{route.prefix} → {route.next_hop}",
                        value=f"{route.prefix}",
                        description=f"Next hop: {route.next_hop}"
                    )
                    for route in routes[:25]  # Discord limit 25 options
                ]
            )
            async def select_callback(self, select_interaction: discord.Interaction, select: discord.ui.Select):
                await select_interaction.response.defer()
                
                # Find selected route
                selected_prefix = select.values[0]
                selected_route = next((r for r in routes if r.prefix == selected_prefix), None)
                
                if not selected_route:
                    await select_interaction.followup.send(
                        embed=create_error_embed(title="❌ Error", description="Route not found"),
                        ephemeral=True
                    )
                    return
                
                # Extract netmask from prefix (e.g., "192.168.10.0/24" -> "24")
                prefix_parts = selected_route.prefix.split('/')
                prefix_addr = prefix_parts[0]
                netmask = prefix_parts[1] if len(prefix_parts) > 1 else "32"
                
                # Delete the route
                try:
                    await service.routing.delete_static_route(prefix_addr, netmask)
                    embed = create_success_embed(
                        title="✅ Static Route Deleted",
                        description=f"Successfully deleted static route on **{creds.host}**"
                    )
                    embed.add_field(
                        name="📍 Network",
                        value=f"`{selected_route.prefix}`",
                        inline=False
                    )
                    embed.add_field(
                        name="➜ Next Hop",
                        value=f"`{selected_route.next_hop}`",
                        inline=False
                    )
                    await select_interaction.followup.send(embed=embed)
                    self.stop()
                except RestconfError as exc:
                    await select_interaction.followup.send(
                        embed=render_restconf_error(str(exc)),
                        ephemeral=True
                    )
        
        # Send the selection menu
        embed = discord.Embed(
            title="🗑️ Delete Static Route",
            description=f"เลือก route ที่ต้องการลบจาก **{creds.host}**",
            color=discord.Color.blue()
        )
        view = RouteSelectView()
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
