"""Slash command registrations for connection management."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.connection_manager import ConnectionManager
from restconf.errors import RestconfConnectionError, RestconfHTTPError
from restconf.services.connection import ConnectionResult, ConnectionService
from infrastructure.messaging.rabbitmq import RabbitMQClient
from infrastructure.mongodb.router_store import MongoRouterStore
from utils.embeds import create_success_embed, create_error_embed, create_info_embed
from utils.logger import get_logger

_logger = get_logger(__name__)


def _build_connect_command(
    connection_manager: ConnectionManager,
    connection_service: ConnectionService,
    router_store: Optional[MongoRouterStore],
    message_client: Optional[RabbitMQClient],
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
        if host is None or username is None or password is None:
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

            storage_note = ""
            guild_id = interaction.guild_id
            if router_store and guild_id is not None:
                try:
                    await router_store.upsert_router(
                        {
                            "guild_id": guild_id,
                            "ip": result.host,
                            "hostname": result.hostname,
                            "username": username,
                            "password": password,
                            "name": result.hostname or result.host,
                            "last_connected_at": datetime.utcnow(),
                        }
                    )
                    storage_note = "\n\nStored router profile for quick reconnect."
                except Exception as store_error:  # pragma: no cover - best effort logging
                    _logger.warning(
                        "Failed to persist router profile for guild %s (%s): %s",
                        guild_id,
                        result.host,
                        store_error,
                    )

            if message_client and guild_id is not None:
                try:
                    await message_client.publish_event(
                        "router.connection.success",
                        {
                            "guild_id": guild_id,
                            "ip": result.host,
                            "hostname": result.hostname,
                            "username": username,
                        },
                    )
                except Exception as publish_error:  # pragma: no cover - best effort logging
                    _logger.warning(
                        "Failed to publish connection event for guild %s (%s): %s",
                        guild_id,
                        result.host,
                        publish_error,
                    )

            description = (
                "Successfully connected to router: **{host}**\n"
                "Hostname: **{hostname}**\n\n"
                "All RESTCONF commands will now use this connection."
            ).format(host=result.host, hostname=result.hostname)
            if storage_note:
                description += storage_note

            embed = create_success_embed(
                title="✅ Connection Successful",
                description=description,
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


def _build_router_list_command(
    connection_manager: ConnectionManager,
    connection_service: ConnectionService,
    router_store: Optional[MongoRouterStore],
    message_client: Optional[RabbitMQClient],
) -> app_commands.Command:
    @app_commands.command(
        name="get-router-list",
        description="List stored routers and optionally switch to one",
    )
    @app_commands.describe(target="Router IP address or hostname to switch to")
    async def command(interaction: discord.Interaction, target: Optional[str] = None) -> None:
        await interaction.response.defer(thinking=True)

        if router_store is None:
            embed = create_error_embed(
                title="❌ Storage Unavailable",
                description="Router persistence is not configured for this deployment.",
            )
            await interaction.followup.send(embed=embed)
            return

        guild_id = interaction.guild_id
        if guild_id is None:
            embed = create_error_embed(
                title="❌ Server Only",
                description="This command is only available within a Discord server.",
            )
            await interaction.followup.send(embed=embed)
            return

        routers = await router_store.list_routers(guild_id)
        current_host = connection_manager.get_host()

        if target is None:
            if not routers:
                embed = create_info_embed(
                    title="ℹ️ No Stored Routers",
                    description=(
                        "No routers have been stored yet. Connect with `/connect` to save the current router."
                    ),
                )
                await interaction.followup.send(embed=embed)
                return

            lines = []
            for router in routers:
                hostname = router.get("hostname") or router.get("name") or router.get("ip")
                ip = router.get("ip", "unknown")
                username = router.get("username", "?")
                marker = " (current)" if current_host and current_host == ip else ""
                lines.append(f"• **{hostname}** — `{ip}` (user `{username}`){marker}")

            embed = create_info_embed(
                title="🗂️ Stored Routers",
                description="\n".join(lines) + "\n\nProvide a `target` to switch to one of them.",
            )
            await interaction.followup.send(embed=embed)
            return

        router = next(
            (
                r
                for r in routers
                if target == r.get("ip")
                or target == r.get("hostname")
                or target == r.get("name")
            ),
            None,
        )

        if router is None:
            embed = create_error_embed(
                title="❌ Router Not Found",
                description=(
                    f"Could not find a stored router matching `{target}`. Use `/get-router-list` without a target"
                    " to view all stored routers."
                ),
            )
            await interaction.followup.send(embed=embed)
            return

        stored_username = router.get("username")
        stored_password = router.get("password")
        stored_ip = router.get("ip")

        if not stored_username or not stored_password or not stored_ip:
            embed = create_error_embed(
                title="❌ Incomplete Router Profile",
                description="The stored router does not have the required credentials to reconnect.",
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            result = await connection_service.connect(stored_ip, stored_username, stored_password)

            try:
                await router_store.upsert_router(
                    {
                        "guild_id": guild_id,
                        "ip": stored_ip,
                        "hostname": result.hostname,
                        "username": stored_username,
                        "password": stored_password,
                        "name": router.get("name") or result.hostname or stored_ip,
                        "last_connected_at": datetime.utcnow(),
                    }
                )
            except Exception as store_error:  # pragma: no cover - best effort logging
                _logger.warning(
                    "Failed to update router profile for guild %s (%s): %s",
                    guild_id,
                    stored_ip,
                    store_error,
                )

            embed = create_success_embed(
                title="✅ Switched Router",
                description=(
                    "Now connected to router: **{host}**\nHostname: **{hostname}**\n\n"
                    "All RESTCONF commands will now use this connection."
                ).format(host=result.host, hostname=result.hostname),
            )
            await interaction.followup.send(embed=embed)

            if message_client:
                try:
                    await message_client.publish_event(
                        "router.connection.switched",
                        {
                            "guild_id": guild_id,
                            "ip": result.host,
                            "hostname": result.hostname,
                            "username": stored_username,
                        },
                    )
                except Exception as publish_error:  # pragma: no cover - best effort logging
                    _logger.warning(
                        "Failed to publish router switch event for guild %s (%s): %s",
                        guild_id,
                        stored_ip,
                        publish_error,
                    )

        except RestconfConnectionError as e:
            embed = create_error_embed(
                title="❌ Connection Failed",
                description=(
                    f"Could not connect to stored router **{stored_ip}**\n\n"
                    f"**Error:** {str(e)}\n\n"
                    "The stored credentials may be outdated."
                ),
            )
            await interaction.followup.send(embed=embed)

        except RestconfHTTPError as e:
            embed = create_error_embed(
                title="❌ Authentication Failed",
                description=(
                    f"Authentication failed for stored router **{stored_ip}**\n\n"
                    f"**Error:** {str(e)}\n\n"
                    "Please verify the stored username and password."
                ),
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = create_error_embed(
                title="❌ Unexpected Error",
                description=f"An unexpected error occurred while switching routers:\n\n```{str(e)}```",
            )
            await interaction.followup.send(embed=embed)

    @command.autocomplete("target")
    async def target_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        if router_store is None or interaction.guild_id is None:
            return []

        try:
            routers = await router_store.list_routers(interaction.guild_id)
        except Exception as exc:  # pragma: no cover - best effort, avoid failing autocomplete
            _logger.warning(
                "Failed to fetch routers for autocomplete (guild=%s): %s",
                interaction.guild_id,
                exc,
            )
            return []

        normalized = current.lower()
        choices: list[app_commands.Choice[str]] = []
        for router in routers:
            name = router.get("name") or router.get("hostname") or router.get("ip")
            ip = router.get("ip")
            if not ip or not name:
                continue

            if normalized and normalized not in name.lower() and normalized not in ip.lower():
                continue

            label = f"{name} ({ip})"
            choices.append(app_commands.Choice(name=label[:100], value=ip))
            if len(choices) >= 25:
                break

        return choices

    return command


class ConnectionCommandGroup(CommandGroup):
    def __init__(
        self,
        connection_manager: ConnectionManager,
        connection_service: ConnectionService,
        router_store: Optional[MongoRouterStore] = None,
        message_client: Optional[RabbitMQClient] = None,
    ) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_connect_command(connection_manager, connection_service, router_store, message_client),
            _build_disconnect_command(connection_service),
            _build_router_list_command(connection_manager, connection_service, router_store, message_client),
        ]
        super().__init__(commands)
