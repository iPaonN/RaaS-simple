"""Domain name command builders for RESTCONF device operations."""
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
from restconf.presenters import render_domain_name
from utils.embeds import create_success_embed


def build_get_domain_name_command(
    service_builder: ServiceBuilder,
    connection_manager: ConnectionManager,
) -> app_commands.Command:
    @app_commands.command(name="get-domain-name", description="Get domain name configuration")
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
            domain = await context.service.fetch_domain_name()
        except RestconfError as exc:
            await send_restconf_failure(interaction, exc)
            return

        await interaction.followup.send(embed=render_domain_name(context.credentials.host, domain))

    return command


def build_set_domain_name_command(
    service_builder: ServiceBuilder,
    connection_manager: ConnectionManager,
) -> app_commands.Command:
    @app_commands.command(name="set-domain-name", description="Set domain name configuration")
    @app_commands.describe(
        domain="Domain name (e.g., example.com)",
        host="Router IP address or hostname (optional if connected)",
        username="RESTCONF username (optional if connected)",
        password="RESTCONF password (optional if connected)",
    )
    async def command(
        interaction: discord.Interaction,
        domain: str,
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
            await context.service.update_domain_name(domain)
        except RestconfError as exc:
            await send_restconf_failure(interaction, exc)
            return

        success_embed = create_success_embed(
            title="✅ Domain Name Updated",
            description=f"Domain name has been updated successfully on **{context.credentials.host}**",
        )
        success_embed.add_field(
            name="New Domain",
            value=f"`{domain}`",
            inline=False,
        )
        await interaction.followup.send(embed=success_embed)

    return command
