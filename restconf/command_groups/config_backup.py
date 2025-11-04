"""Configuration restore command builder."""
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

_VALID_EXTENSIONS = (".txt", ".cfg", ".conf")


def build_backup_command(
    connection_manager: ConnectionManager,
    service_builder: ConfigServiceBuilder,
) -> app_commands.Command:
    @app_commands.command(name="backup", description="Restore running configuration to router from uploaded file")
    @app_commands.describe(
        config_file="Text file containing router configuration",
        host="Router IP address or hostname (optional if connected)",
        username="SSH username (optional if connected)",
        password="SSH password (optional if connected)",
    )
    async def command(
        interaction: discord.Interaction,
        config_file: discord.Attachment,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(thinking=True)

        if not config_file.filename.lower().endswith(_VALID_EXTENSIONS):
            embed = create_error_embed(
                title="❌ Invalid File Type",
                description="Please upload a text file with extension `.txt`, `.cfg`, or `.conf`",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

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
            config_content = await config_file.read()
            config_text = config_content.decode("utf-8")
        except Exception as exc:  # pragma: no cover - attachment retrieval failure
            embed = create_error_embed(
                title="❌ File Read Error",
                description=f"Failed to read uploaded file\n\nError: `{str(exc)}`",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            result = await context.service.restore_config(config_text)
        except Exception as exc:  # pragma: no cover - network/device error path
            embed = create_error_embed(
                title="❌ Restore Failed",
                description=(
                    f"Failed to restore configuration to **{context.credentials.host}**"
                    f"\n\nError: `{str(exc)}`"
                ),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = create_success_embed(
            title="✅ Configuration Restored",
            description=f"Successfully applied configuration to **{context.credentials.host}**",
        )
        embed.add_field(name="📄 File", value=f"`{config_file.filename}`", inline=False)
        preview = result[:500]
        if len(result) > 500:
            preview = f"{preview}...\n(truncated)"
        embed.add_field(name="📊 Result", value=f"```{preview}```", inline=False)
        await interaction.followup.send(embed=embed)

    return command
