"""Command builder for listing and switching stored routers."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import discord
from discord import app_commands

from infrastructure.messaging.rabbitmq import RabbitMQClient
from infrastructure.mongodb.router_store import MongoRouterStore
from restconf.connection_manager import ConnectionManager
from restconf.errors import RestconfConnectionError, RestconfHTTPError
from restconf.services.connection import ConnectionService
from utils.embeds import create_error_embed, create_info_embed, create_success_embed
from utils.logger import get_logger

_logger = get_logger(__name__)

_STATUS_EMOJI = {
    "online": "🟢",
    "offline": "🔴",
    "auth_failed": "⚠️",
    "invalid": "⚠️",
    "error": "❗",
    "unknown": "❔",
}


async def _remove_stored_router(
    router_store: MongoRouterStore,
    guild_id: int,
    ip: str,
    reason: str,
    error: Exception,
) -> None:
    try:
        deleted = await router_store.delete_router(guild_id, ip)
        if deleted:
            _logger.info(
                "Removed stored router %s for guild %s after %s failure: %s",
                ip,
                guild_id,
                reason,
                error,
            )
        else:  # pragma: no cover - benign mismatch
            _logger.info(
                "No stored router found to remove for guild %s (%s) after %s failure",
                guild_id,
                ip,
                reason,
            )
    except Exception as removal_error:  # pragma: no cover - best effort cleanup
        _logger.warning(
            "Failed to remove stored router %s for guild %s after %s failure: %s",
            ip,
            guild_id,
            reason,
            removal_error,
        )


def build_router_list_command(
    connection_manager: ConnectionManager,
    connection_service: ConnectionService,
    router_store: Optional[MongoRouterStore],
    message_client: Optional[RabbitMQClient],
) -> app_commands.Command:
    """Build the slash command that manages saved router profiles."""

    @app_commands.command(
        name="get-router-list",
        description="List stored routers and optionally switch to one",
    )
    @app_commands.describe(target="Router IP address or hostname to switch to")
    async def command(
        interaction: discord.Interaction,
        target: Optional[str] = None,
    ) -> None:
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
                status = (router.get("status") or "unknown").lower()
                status_label = status.replace("_", " ")
                emoji = _STATUS_EMOJI.get(status, "❔")
                last_seen = router.get("last_seen")
                if isinstance(last_seen, datetime):
                    last_seen_text = last_seen.strftime("%Y-%m-%d %H:%M UTC")
                    last_seen_fragment = f" • last seen {last_seen_text}"
                else:
                    last_seen_fragment = ""
                reason = router.get("status_reason")
                reason_fragment = f"\n   ↳ {reason}" if reason else ""
                lines.append(
                    (
                        f"• {emoji} **{hostname}** — `{ip}` (user `{username}`){marker}"
                        f" • status: {status_label}{last_seen_fragment}{reason_fragment}"
                    )
                )

            embed = create_info_embed(
                title="🗂️ Stored Routers",
                description="\n".join(lines) + "\n\nProvide a `target` to switch to one of them.",
            )
            await interaction.followup.send(embed=embed)
            return

        router = next(
            (
                stored
                for stored in routers
                if target == stored.get("ip")
                or target == stored.get("hostname")
                or target == stored.get("name")
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

        except RestconfConnectionError as err:
            await _remove_stored_router(router_store, guild_id, stored_ip, "connection", err)
            embed = create_error_embed(
                title="❌ Connection Failed",
                description=(
                    f"Could not connect to stored router **{stored_ip}**\n\n"
                    f"**Error:** {err}\n\n"
                    "The router has been removed from your saved list. Use `/connect` again once it is reachable."
                ),
            )
            await interaction.followup.send(embed=embed)

        except RestconfHTTPError as err:
            await _remove_stored_router(router_store, guild_id, stored_ip, "authentication", err)
            embed = create_error_embed(
                title="❌ Authentication Failed",
                description=(
                    f"Authentication failed for stored router **{stored_ip}**\n\n"
                    f"**Error:** {err}\n\n"
                    "The router has been removed from your saved list. Use `/connect` again with updated credentials."
                ),
            )
            await interaction.followup.send(embed=embed)

        except Exception as err:  # pragma: no cover - resiliency
            embed = create_error_embed(
                title="❌ Unexpected Error",
                description=f"An unexpected error occurred while switching routers:\n\n```{err}```",
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
        except Exception as err:  # pragma: no cover - best effort
            _logger.warning(
                "Failed to fetch routers for autocomplete (guild=%s): %s",
                interaction.guild_id,
                err,
            )
            return []

        normalized = current.lower()
        choices: list[app_commands.Choice[str]] = []
        for stored in routers:
            name = stored.get("name") or stored.get("hostname") or stored.get("ip")
            ip = stored.get("ip")
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
