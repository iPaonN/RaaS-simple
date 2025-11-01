"""Slash command registrations for interface management."""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.connection_manager import ConnectionManager
from restconf.errors import RestconfError, RestconfNotFoundError
from restconf.presenters import (
    render_interface,
    render_interface_list,
    render_restconf_error,
)
from restconf.service import RestconfService
from utils.embeds import create_error_embed

ServiceBuilder = Callable[[str, str, str], RestconfService]


async def interface_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """Autocomplete function to suggest available interfaces."""
    # Get connection from the cog's connection manager
    try:
        # Access the connection manager through the bot
        from cogs.restconf import RestconfCog
        cog = interaction.client.get_cog("RestconfCog")
        if not cog or not hasattr(cog, '_connection_manager'):
            return []
        
        conn = cog._connection_manager.get_connection()
        if not conn:
            return []
        
        # Build service and fetch interfaces
        from restconf.client import RestconfClient
        client = RestconfClient(conn.host, conn.username, conn.password)
        service = RestconfService(client)
        
        interfaces = await service.fetch_interfaces()
        
        # Filter interfaces by current input and return up to 25 choices
        filtered = [
            app_commands.Choice(name=iface.name, value=iface.name)
            for iface in interfaces
            if current.lower() in iface.name.lower()
        ]
        return filtered[:25]  # Discord limit
    except Exception:
        return []


def _build_get_interfaces(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="get-interfaces", description="Get all interfaces from CSR1000v")
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
        
        # Fill missing parameters from stored connection (allow partial overrides)
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
            if host is None:
                host = conn.host
            if username is None:
                username = conn.username
            if password is None:
                password = conn.password
        
        service = service_builder(host, username, password)
        try:
            interfaces = await service.fetch_interfaces()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_interface_list(host, interfaces))

    return command


def _build_get_interface(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="get-interface", description="Get specific interface details")
    @app_commands.describe(
        interface="Interface name (e.g., GigabitEthernet1)",
        host="Router IP address or hostname (optional if connected)",
        username="RESTCONF username (optional if connected)",
        password="RESTCONF password (optional if connected)",
    )
    @app_commands.autocomplete(interface=interface_autocomplete)
    async def command(
        interaction: discord.Interaction,
        interface: str,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        
        # Fill missing parameters from stored connection (allow partial overrides)
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
            if host is None:
                host = conn.host
            if username is None:
                username = conn.username
            if password is None:
                password = conn.password
        
        service = service_builder(host, username, password)
        try:
            model = await service.fetch_interface(interface)
        except RestconfNotFoundError:
            await interaction.followup.send(
                embed=render_restconf_error(f"Interface `{interface}` not found."),
                ephemeral=True,
            )
            return
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_interface(host, model))

    return command


def _build_set_interface_description(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="set-interface-description", description="Set interface description")
    @app_commands.describe(
        interface="Interface name (e.g., GigabitEthernet1)",
        description="New interface description",
        host="Router IP address or hostname (optional if connected)",
        username="RESTCONF username (optional if connected)",
        password="RESTCONF password (optional if connected)",
    )
    @app_commands.autocomplete(interface=interface_autocomplete)
    async def command(
        interaction: discord.Interaction,
        interface: str,
        description: str,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        
        # Fill missing parameters from stored connection (allow partial overrides)
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
            if host is None:
                host = conn.host
            if username is None:
                username = conn.username
            if password is None:
                password = conn.password
        
        service = service_builder(host, username, password)
        try:
            model = await service.update_interface_description(interface, description)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        embed = render_interface(host, model)
        embed.title = "✅ Interface Updated"
        await interaction.followup.send(embed=embed)

    return command


def _build_set_interface_state(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="set-interface-state", description="Enable or disable an interface")
    @app_commands.describe(
        interface="Interface name (e.g., GigabitEthernet1)",
        enabled="Enable (True) or disable (False) the interface",
        host="Router IP address or hostname (optional if connected)",
        username="RESTCONF username (optional if connected)",
        password="RESTCONF password (optional if connected)",
    )
    @app_commands.autocomplete(interface=interface_autocomplete)
    async def command(
        interaction: discord.Interaction,
        interface: str,
        enabled: bool,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        
        # Fill missing parameters from stored connection (allow partial overrides)
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
            if host is None:
                host = conn.host
            if username is None:
                username = conn.username
            if password is None:
                password = conn.password
        
        service = service_builder(host, username, password)
        try:
            model = await service.update_interface_state(interface, enabled)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        embed = render_interface(host, model)
        status = "Enabled" if enabled else "Disabled"
        embed.title = f"✅ Interface {status}"
        await interaction.followup.send(embed=embed)

    return command


def _build_set_interface_ip(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="set-interface-ip", description="Configure interface IP address")
    @app_commands.describe(
        interface="Interface name (e.g., GigabitEthernet1)",
        ip_address="IP address (e.g., 192.168.1.1)",
        netmask="Subnet mask (e.g., 255.255.255.0)",
        host="Router IP address or hostname (optional if connected)",
        username="RESTCONF username (optional if connected)",
        password="RESTCONF password (optional if connected)",
    )
    @app_commands.autocomplete(interface=interface_autocomplete)
    async def command(
        interaction: discord.Interaction,
        interface: str,
        ip_address: str,
        netmask: str,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        
        # Fill missing parameters from stored connection (allow partial overrides)
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
            if host is None:
                host = conn.host
            if username is None:
                username = conn.username
            if password is None:
                password = conn.password
        
        service = service_builder(host, username, password)
        try:
            model = await service.update_interface_ip(interface, ip_address, netmask)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        embed = render_interface(host, model)
        embed.title = "✅ IP Address Configured"
        await interaction.followup.send(embed=embed)

    return command


class InterfaceCommandGroup(CommandGroup):
    def __init__(self, service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_get_interfaces(service_builder, connection_manager),
            _build_get_interface(service_builder, connection_manager),
            _build_set_interface_description(service_builder, connection_manager),
            _build_set_interface_state(service_builder, connection_manager),
            _build_set_interface_ip(service_builder, connection_manager),
        ]
        super().__init__(commands)
