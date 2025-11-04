"""Command builder for the `/connect` RESTCONF command."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import discord
from discord import app_commands

from infrastructure.messaging.rabbitmq import RabbitMQClient
from infrastructure.mongodb.router_store import MongoRouterStore
from restconf.connection_manager import ConnectionManager
from restconf.errors import RestconfConnectionError, RestconfHTTPError
from restconf.services.connection import ConnectionResult, ConnectionService
from utils.embeds import create_error_embed, create_info_embed, create_success_embed
from utils.logger import get_logger

_logger = get_logger(__name__)


def build_connect_command(
    connection_manager: ConnectionManager,
    connection_service: ConnectionService,
    router_store: Optional[MongoRouterStore],
    message_client: Optional[RabbitMQClient],
) -> app_commands.Command:
    """Build the slash command that manages router connections."""

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

        if host is None and username is None and password is None:
            connection = connection_manager.get_connection()

            if connection:
                embed = create_info_embed(
                    title="🔌 Current Connection",
                    description=(
                        "Connected to router: **{host}**\n"
                        "**Username:** `{username}`"
                    ).format(host=connection.host, username=connection.username),
                )
            else:
                embed = create_info_embed(
                    title="🔌 No Connection",
                    description="No router is currently connected.\n\nUse `/connect [host] [username] [password]` to connect.",
                )

            await interaction.followup.send(embed=embed)
            return

        if host is None or username is None or password is None:
            embed = create_error_embed(
                title="❌ Invalid Parameters",
                description=(
                    "Please provide all three parameters: **host**, **username**, and **password**.\n\n"
                    "Example: `/connect 192.168.1.1 admin cisco123`"
                ),
            )
            await interaction.followup.send(embed=embed)
            return

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

        except RestconfConnectionError as err:
            embed = create_error_embed(
                title="❌ Connection Failed",
                description=(
                    f"Could not connect to router **{host}**\n\n"
                    f"**Error:** {err}\n\n"
                    "Please check:\n"
                    "• Router IP address is correct\n"
                    "• Router is reachable\n"
                    "• RESTCONF is enabled on the router"
                ),
            )
            await interaction.followup.send(embed=embed)

        except RestconfHTTPError as err:
            embed = create_error_embed(
                title="❌ Authentication Failed",
                description=(
                    f"Connected to **{host}** but authentication failed.\n\n"
                    f"**Error:** {err}\n\n"
                    "Please check:\n"
                    "• Username is correct\n"
                    "• Password is correct\n"
                    "• User has proper privileges"
                ),
            )
            await interaction.followup.send(embed=embed)

        except Exception as err:  # pragma: no cover - resiliency
            embed = create_error_embed(
                title="❌ Unexpected Error",
                description=f"An unexpected error occurred:\n\n```{err}```",
            )
            await interaction.followup.send(embed=embed)

    return command
