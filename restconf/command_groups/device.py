"""Slash command registrations for device configuration."""
from __future__ import annotations

from typing import Callable, Optional, Sequence

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.connection_manager import ConnectionManager
from restconf.errors import RestconfError
from restconf.presenters import (
    render_banner,
    render_domain_name,
    render_hostname,
    render_name_servers,
    render_restconf_error,
)
from restconf.service import RestconfService
from utils.embeds import create_error_embed, create_success_embed

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


def _build_get_banner_motd(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="get-banner-motd", description="Get Message of the Day banner")
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
            banner = await service.fetch_banner_motd()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_banner(host, banner))

    return command


def _build_set_banner_motd(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="set-banner-motd", description="Set Message of the Day banner")
    @app_commands.describe(
        message="Banner message text",
        host="Router IP address or hostname (optional if connected)",
        username="RESTCONF username (optional if connected)",
        password="RESTCONF password (optional if connected)",
    )
    async def command(
        interaction: discord.Interaction,
        message: str,
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
            banner = await service.update_banner_motd(message)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        
        # Create success embed
        from utils.embeds import create_success_embed
        success_embed = create_success_embed(
            title="✅ Banner Updated",
            description=f"MOTD banner has been updated successfully on **{host}**"
        )
        success_embed.add_field(
            name="New Banner",
            value=f"```\n{message[:500]}\n```",
            inline=False
        )
        await interaction.followup.send(embed=success_embed)

    return command


def _build_get_domain_name(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="get-domain-name", description="Get domain name configuration")
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
            domain = await service.fetch_domain_name()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_domain_name(host, domain))

    return command


def _build_set_domain_name(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="set-domain-name", description="Set domain name configuration")
    @app_commands.describe(
        domain="Domain name (e.g., example.com)",
        host="Router IP address or hostname (optional if connected)",
        username="RESTCONF username (optional if connected)",
        password="RESTCONF password (optional if connected)",
    )
    async def command(
        interaction: discord.Interaction,
        domain: str,
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
            domain_obj = await service.update_domain_name(domain)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        
        # Create success embed
        success_embed = create_success_embed(
            title="✅ Domain Name Updated",
            description=f"Domain name has been updated successfully on **{host}**"
        )
        success_embed.add_field(
            name="New Domain",
            value=f"`{domain}`",
            inline=False
        )
        await interaction.followup.send(embed=success_embed)

    return command


def _build_get_name_servers(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="get-name-servers", description="Get DNS name server configuration")
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
            name_servers = await service.fetch_name_servers()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_name_servers(host, name_servers))

    return command


def _build_save_config(service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="save-config", description="Save running configuration to startup configuration")
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
            await service.save_config()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        
        # Create success embed
        success_embed = create_success_embed(
            title="✅ Configuration Saved",
            description=f"Running configuration has been successfully saved to startup configuration on **{host}**"
        )
        success_embed.add_field(
            name="📝 Note",
            value="Changes will persist after device reload",
            inline=False
        )
        await interaction.followup.send(embed=success_embed)

    return command


class DeviceCommandGroup(CommandGroup):
    def __init__(self, service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_get_hostname(service_builder, connection_manager),
            _build_set_hostname(service_builder, connection_manager),
            _build_get_banner_motd(service_builder, connection_manager),
            _build_set_banner_motd(service_builder, connection_manager),
            _build_get_domain_name(service_builder, connection_manager),
            _build_set_domain_name(service_builder, connection_manager),
            _build_get_name_servers(service_builder, connection_manager),
            _build_save_config(service_builder, connection_manager),
        ]
        super().__init__(commands)