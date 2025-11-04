"""Running configuration backup command builder."""
from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands

from restconf.command_groups.config_shared import (
    ConfigServiceBuilder,
    resolve_config_context,
)
from restconf.connection_manager import ConnectionManager
from utils.embeds import create_error_embed, create_success_embed


def build_get_config_command(
    connection_manager: ConnectionManager,
    service_builder: ConfigServiceBuilder,
) -> app_commands.Command:
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

        context = await resolve_config_context(
            interaction,
            connection_manager,
            service_builder,
            host,
            username,
            password,
        )
        if context is None:
            return

        try:
            config_path = await context.service.get_running_config()
        except Exception as exc:  # pragma: no cover - network/device error path
            embed = create_error_embed(
                title="❌ Backup Failed",
                description=(
                    f"Failed to get configuration from **{context.credentials.host}**\n\nError: `{str(exc)}`"
                ),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        file_attachment = discord.File(str(config_path))
        embed = create_success_embed(
            title="✅ Configuration Backup",
            description=(
                "Successfully retrieved running configuration from "
                f"**{context.credentials.host}**"
            ),
        )
        embed.add_field(name="📄 File", value=f"`{config_path.name}`", inline=False)
        await interaction.followup.send(embed=embed, file=file_attachment)

    return command
