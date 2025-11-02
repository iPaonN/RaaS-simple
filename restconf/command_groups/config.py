"""Slash command registrations for configuration operations."""
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
from netmiko_client import ConfigService
from utils.embeds import create_error_embed, create_success_embed

ConfigServiceBuilder = Callable[[str, str, str], ConfigService]


def _build_get_config(connection_manager: ConnectionManager) -> app_commands.Command:
    @app_commands.command(name="get-config", description="Backup running configuration from router")
    @app_commands.describe(
        host="Router IP address or hostname (optional if connected)",
        username="SSH username (optional if connected)",
        password="SSH password (optional if connected)",
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
        
        # Create config service
        config_service = ConfigService(creds.host, creds.username, creds.password)
        
        try:
            # Get configuration
            config_path = await config_service.get_running_config()
            
            # Send file to Discord
            file = discord.File(str(config_path))
            embed = create_success_embed(
                title="✅ Configuration Backup",
                description=f"Successfully retrieved running configuration from **{creds.host}**"
            )
            embed.add_field(
                name="📄 File",
                value=f"`{config_path.name}`",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, file=file)
            
        except Exception as exc:
            embed = create_error_embed(
                title="❌ Backup Failed",
                description=f"Failed to get configuration from **{creds.host}**\n\nError: `{str(exc)}`"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    return command


class ConfigCommandGroup(CommandGroup):
    def __init__(self, connection_manager: ConnectionManager) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_get_config(connection_manager),
        ]
        super().__init__(commands)
