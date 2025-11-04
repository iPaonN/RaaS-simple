"""Command builder for the `/disconnect` RESTCONF command."""
from __future__ import annotations

import discord
from discord import app_commands

from restconf.services.connection import ConnectionService
from utils.embeds import create_info_embed, create_success_embed


def build_disconnect_command(connection_service: ConnectionService) -> app_commands.Command:
    """Build the slash command that severs the active router connection."""

    @app_commands.command(name="disconnect", description="Disconnect from the current router")
    async def command(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        connection = connection_service.get_connection()
        if not connection:
            embed = create_info_embed(
                title="ℹ️ No Connection",
                description="No router is currently connected.",
            )
            await interaction.followup.send(embed=embed)
            return

        connection_service.disconnect()

        embed = create_success_embed(
            title="✅ Disconnected",
            description=f"Disconnected from router: **{connection.host}**",
        )
        await interaction.followup.send(embed=embed)

    return command
