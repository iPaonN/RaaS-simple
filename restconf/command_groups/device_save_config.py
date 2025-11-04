"""Configuration persistence command builder for RESTCONF device operations."""
from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands

from restconf.command_groups.device_shared import (
    ServiceBuilder,
    resolve_device_context,
    send_restconf_failure,
)
from restconf.connection_manager import ConnectionManager
from restconf.errors import RestconfError
from utils.embeds import create_success_embed


def build_save_config_command(
    service_builder: ServiceBuilder,
    connection_manager: ConnectionManager,
) -> app_commands.Command:
    @app_commands.command(
        name="save-config",
        description="Save running configuration to startup configuration",
    )
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

        context = await resolve_device_context(
            interaction,
            service_builder,
            connection_manager,
            host,
            username,
            password,
        )
        if context is None:
            return

        try:
            await context.service.save_config()
        except RestconfError as exc:
            await send_restconf_failure(interaction, exc)
            return

        success_embed = create_success_embed(
            title="✅ Configuration Saved",
            description=(
                "Running configuration has been successfully saved to startup configuration"
                f" on **{context.credentials.host}**"
            ),
        )
        success_embed.add_field(
            name="📝 Note",
            value="Changes will persist after device reload",
            inline=False,
        )
        await interaction.followup.send(embed=success_embed)

    return command
