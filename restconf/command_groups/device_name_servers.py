"""DNS name server command builders for RESTCONF device operations."""
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
from restconf.presenters import render_name_servers


def build_get_name_servers_command(
    service_builder: ServiceBuilder,
    connection_manager: ConnectionManager,
) -> app_commands.Command:
    @app_commands.command(name="get-name-servers", description="Get DNS name server configuration")
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
            name_servers = await context.service.fetch_name_servers()
        except RestconfError as exc:
            await send_restconf_failure(interaction, exc)
            return

        await interaction.followup.send(embed=render_name_servers(context.credentials.host, name_servers))

    return command
