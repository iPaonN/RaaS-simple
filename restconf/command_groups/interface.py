"""Slash command registrations for interface management."""
from __future__ import annotations

from typing import Callable, Sequence

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.errors import RestconfError, RestconfNotFoundError
from restconf.presenters import (
    render_interface,
    render_interface_list,
    render_restconf_error,
)
from restconf.service import RestconfService

ServiceBuilder = Callable[[str, str, str], RestconfService]


def _build_get_interfaces(service_builder: ServiceBuilder) -> app_commands.Command:
    @app_commands.command(name="get-interfaces", description="Get all interfaces from CSR1000v")
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
            interfaces = await service.fetch_interfaces()
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_interface_list(host, interfaces))

    return command


def _build_get_interface(service_builder: ServiceBuilder) -> app_commands.Command:
    @app_commands.command(name="get-interface", description="Get specific interface details")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
        interface="Interface name (e.g., GigabitEthernet1)",
    )
    async def command(
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
        interface: str,
    ) -> None:
        await interaction.response.defer(thinking=True)
        service = service_builder(host, username, password)
        try:
            model = await service.fetch_interface(interface)
        except RestconfNotFoundError:
            await interaction.followup.send(
                embed=render_restconf_error(f"Interface `{interface}` not found."),
                ephemeral=True,
            )
            return
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        await interaction.followup.send(embed=render_interface(host, model))

    return command


def _build_set_interface_description(service_builder: ServiceBuilder) -> app_commands.Command:
    @app_commands.command(name="set-interface-description", description="Set interface description")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
        interface="Interface name (e.g., GigabitEthernet1)",
        description="New interface description",
    )
    async def command(
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
        interface: str,
        description: str,
    ) -> None:
        await interaction.response.defer(thinking=True)
        service = service_builder(host, username, password)
        try:
            model = await service.update_interface_description(interface, description)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        embed = render_interface(host, model)
        embed.title = "✅ Interface Updated"
        await interaction.followup.send(embed=embed)

    return command


def _build_set_interface_state(service_builder: ServiceBuilder) -> app_commands.Command:
    @app_commands.command(name="set-interface-state", description="Enable or disable an interface")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
        interface="Interface name (e.g., GigabitEthernet1)",
        enabled="Enable (True) or disable (False) the interface",
    )
    async def command(
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
        interface: str,
        enabled: bool,
    ) -> None:
        await interaction.response.defer(thinking=True)
        service = service_builder(host, username, password)
        try:
            model = await service.update_interface_state(interface, enabled)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        embed = render_interface(host, model)
        status = "Enabled" if enabled else "Disabled"
        embed.title = f"✅ Interface {status}"
        await interaction.followup.send(embed=embed)

    return command


def _build_set_interface_ip(service_builder: ServiceBuilder) -> app_commands.Command:
    @app_commands.command(name="set-interface-ip", description="Configure interface IP address")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
        interface="Interface name (e.g., GigabitEthernet1)",
        ip_address="IP address (e.g., 192.168.1.1)",
        netmask="Subnet mask (e.g., 255.255.255.0)",
    )
    async def command(
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
        interface: str,
        ip_address: str,
        netmask: str,
    ) -> None:
        await interaction.response.defer(thinking=True)
        service = service_builder(host, username, password)
        try:
            model = await service.update_interface_ip(interface, ip_address, netmask)
        except RestconfError as exc:
            await interaction.followup.send(embed=render_restconf_error(str(exc)), ephemeral=True)
            return
        embed = render_interface(host, model)
        embed.title = "✅ IP Address Configured"
        await interaction.followup.send(embed=embed)

    return command


class InterfaceCommandGroup(CommandGroup):
    def __init__(self, service_builder: ServiceBuilder) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_get_interfaces(service_builder),
            _build_get_interface(service_builder),
            _build_set_interface_description(service_builder),
            _build_set_interface_state(service_builder),
            _build_set_interface_ip(service_builder),
        ]
        super().__init__(commands)
