"""Banner MOTD command builders for RESTCONF device operations."""
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
from restconf.presenters import render_banner
from utils.embeds import create_success_embed


def build_get_banner_motd_command(
    service_builder: ServiceBuilder,
    connection_manager: ConnectionManager,
) -> app_commands.Command:
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
            banner = await context.service.fetch_banner_motd()
        except RestconfError as exc:
            await send_restconf_failure(interaction, exc)
            return

        await interaction.followup.send(embed=render_banner(context.credentials.host, banner))

    return command


def build_set_banner_motd_command(
    service_builder: ServiceBuilder,
    connection_manager: ConnectionManager,
) -> app_commands.Command:
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
            await context.service.update_banner_motd(message)
        except RestconfError as exc:
            await send_restconf_failure(interaction, exc)
            return

        success_embed = create_success_embed(
            title="✅ Banner Updated",
            description=f"MOTD banner has been updated successfully on **{context.credentials.host}**",
        )
        success_embed.add_field(
            name="New Banner",
            value=f"```\n{message[:500]}\n```",
            inline=False,
        )
        await interaction.followup.send(embed=success_embed)

    return command
