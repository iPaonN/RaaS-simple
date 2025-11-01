"""Slash command registrations for device configuration."""
from __future__ import annotations

from typing import Callable, Sequence

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.errors import RestconfError
from restconf.presenters import render_hostname, render_restconf_error
from restconf.service import RestconfService

ServiceBuilder = Callable[[str, str, str], RestconfService]


def _build_get_hostname(service_builder: ServiceBuilder) -> app_commands.Command:
    @app_commands.command(name="get-hostname", description="Get router hostname")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
    )
    async def command(
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
    ) -> None:
        await interaction.response.defer(thinking=True)
        service = service_builder(host, username, password)
        try:
            hostname = await service.fetch_hostname()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_hostname(host, hostname))

    return command


def _build_set_hostname(service_builder: ServiceBuilder) -> app_commands.Command:
    @app_commands.command(name="set-hostname", description="Set router hostname")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
        hostname="New hostname",
    )
    async def command(
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
        hostname: str,
    ) -> None:
        await interaction.response.defer(thinking=True)
        service = service_builder(host, username, password)
        try:
            hostname_model = await service.update_hostname(hostname)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_hostname(host, hostname_model))

    return command


class DeviceCommandGroup(CommandGroup):
    def __init__(self, service_builder: ServiceBuilder) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_get_hostname(service_builder),
            _build_set_hostname(service_builder),
        ]
        super().__init__(commands)