"""Cog responsible for registering RESTCONF command groups."""
from __future__ import annotations

import discord
from discord.ext import commands

from restconf.client import RestconfClient
from restconf.command_groups import (
    DeviceCommandGroup,
    InterfaceCommandGroup,
    RoutingCommandGroup,
)
from restconf.service import RestconfService
from utils.logger import get_logger

_logger = get_logger(__name__)


class RestconfCog(commands.Cog):
    """Registers RESTCONF-related slash commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._groups = []

    def _service_builder(self, host: str, username: str, password: str) -> RestconfService:
        client = RestconfClient(host, username, password)
        return RestconfService(client)

    async def cog_load(self) -> None:
        group_instances = [
            InterfaceCommandGroup(self._service_builder),
            DeviceCommandGroup(self._service_builder),
            RoutingCommandGroup(self._service_builder),
        ]
        for group in group_instances:
            group.register(self.bot.tree)
        self._groups = group_instances
        _logger.info("Registered RESTCONF command groups")

    async def cog_unload(self) -> None:
        for group in self._groups:
            group.unregister(self.bot.tree)
        _logger.info("Unregistered RESTCONF command groups")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RestconfCog(bot))
