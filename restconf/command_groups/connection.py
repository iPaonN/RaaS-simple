"""Slash command registrations for connection management."""
from __future__ import annotations

from typing import Optional, Sequence

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.connection_manager import ConnectionManager
from restconf.errors import RestconfConnectionError, RestconfHTTPError
from restconf.services.connection import ConnectionResult, ConnectionService
from utils.embeds import create_success_embed, create_error_embed, create_info_embed


def _build_connect_command(
    connection_manager: ConnectionManager,
    connection_service: ConnectionService,
) -> app_commands.Command:
    @app_commands.command(name="connect", description="Connect to a router or show current connection")
    @app_commands.describe(
        host="Router IP address or hostname (optional)",
        username="RESTCONF username (optional)",
        password="RESTCONF password (optional)",
    )
    async def command(
        interaction: discord.Interaction,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        
        # If no parameters provided, show current connection
        if host is None and username is None and password is None:
            connection = connection_manager.get_connection()
            
            if connection:
                embed = create_info_embed(
                    title="🔌 Current Connection",
                    description=(
                        "Connected to router: **{host}**\n"
                        "**Username:** `{username}`"
                    ).format(host=connection.host, username=connection.username)
                )
            else:
                embed = create_info_embed(
                    title="🔌 No Connection",
                    description="No router is currently connected.\n\nUse `/connect [host] [username] [password]` to connect."
                )
            
            await interaction.followup.send(embed=embed)
            return
        
        # Validate that all parameters are provided
        if not all([host, username, password]):
            embed = create_error_embed(
                title="❌ Invalid Parameters",
                description="Please provide all three parameters: **host**, **username**, and **password**.\n\n"
                            "Example: `/connect 192.168.1.1 admin cisco123`"
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Try to connect to the router
        try:
            result: ConnectionResult = await connection_service.connect(host, username, password)

            embed = create_success_embed(
                title="✅ Connection Successful",
                description=(
                    "Successfully connected to router: **{host}**\n"
                    "Hostname: **{hostname}**\n\n"
                    "All RESTCONF commands will now use this connection."
                ).format(host=result.host, hostname=result.hostname),
            )
            await interaction.followup.send(embed=embed)
            
        except RestconfConnectionError as e:
            embed = create_error_embed(
                title="❌ Connection Failed",
                description=f"Could not connect to router **{host}**\n\n"
                            f"**Error:** {str(e)}\n\n"
                            f"Please check:\n"
                            f"• Router IP address is correct\n"
                            f"• Router is reachable\n"
                            f"• RESTCONF is enabled on the router"
            )
            await interaction.followup.send(embed=embed)
            
        except RestconfHTTPError as e:
            embed = create_error_embed(
                title="❌ Authentication Failed",
                description=f"Connected to **{host}** but authentication failed.\n\n"
                            f"**Error:** {str(e)}\n\n"
                            f"Please check:\n"
                            f"• Username is correct\n"
                            f"• Password is correct\n"
                            f"• User has proper privileges"
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = create_error_embed(
                title="❌ Unexpected Error",
                description=f"An unexpected error occurred:\n\n```{str(e)}```"
            )
            await interaction.followup.send(embed=embed)
    
    return command


def _build_disconnect_command(connection_service: ConnectionService) -> app_commands.Command:
    @app_commands.command(name="disconnect", description="Disconnect from the current router")
    async def command(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        
        connection = connection_service.get_connection()
        if not connection:
            embed = create_info_embed(
                title="ℹ️ No Connection",
                description="No router is currently connected."
            )
            await interaction.followup.send(embed=embed)
            return
        
        connection_service.disconnect()
        
        embed = create_success_embed(
            title="✅ Disconnected",
            description=f"Disconnected from router: **{connection.host}**"
        )
        await interaction.followup.send(embed=embed)
    
    return command


class ConnectionCommandGroup(CommandGroup):
    def __init__(self, connection_manager: ConnectionManager, connection_service: ConnectionService) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_connect_command(connection_manager, connection_service),
            _build_disconnect_command(connection_service),
        ]
        super().__init__(commands)
