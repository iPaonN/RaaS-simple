"""Cog responsible for registering RESTCONF command groups."""
from __future__ import annotations

import discord
from discord.ext import commands

from restconf.command_groups import (
    DeviceCommandGroup,
    InterfaceCommandGroup,
    RoutingCommandGroup,
    ConnectionCommandGroup,
    ConfigCommandGroup,
    TaskCommandGroup,
)
from restconf.client import RestconfClient
from restconf.connection_manager import ConnectionManager
from restconf.service import RestconfService
from restconf.services.connection import ConnectionService
from infrastructure.mongodb.router_store import MongoRouterStore
from domain.services.task_service import TaskService
from utils.logger import get_logger

_logger = get_logger(__name__)


class RestconfCog(commands.Cog):
    """Registers RESTCONF-related slash commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._groups = []
        self._connection_manager = ConnectionManager()
        self._connection_service = ConnectionService(self._connection_manager)
        self._router_store: MongoRouterStore | None = getattr(bot, "router_store", None)
        self._task_service: TaskService | None = getattr(bot, "task_service", None)

    def _service_builder(self, host: str, username: str, password: str) -> RestconfService:
        client = RestconfClient(host, username, password)
        return RestconfService(client)

    @property
    def connection_manager(self) -> ConnectionManager:
        """Expose the connection manager for command helpers."""
        return self._connection_manager

    @property
    def connection_service(self) -> ConnectionService:
        """Expose the connection service for helpers that need it."""
        return self._connection_service

    async def cog_load(self) -> None:
        group_instances = [
            ConnectionCommandGroup(
                self._connection_manager,
                self._connection_service,
                self._router_store,
            ),
            InterfaceCommandGroup(self._service_builder, self._connection_manager),
            DeviceCommandGroup(self._service_builder, self._connection_manager),
            RoutingCommandGroup(self._service_builder, self._connection_manager),
            ConfigCommandGroup(self._connection_manager),
            TaskCommandGroup(
                self._router_store,
                self._task_service,
            ),
        ]
        for group in group_instances:
            group.register(self.bot.tree)
        self._groups = group_instances
        _logger.info("Registered RESTCONF command groups")

    async def cog_unload(self) -> None:
        for group in self._groups:
            try:
                group.unregister(self.bot.tree)
            except Exception as e:
                _logger.warning("Failed to unregister command group: %s", e)
        _logger.info("Unregistered RESTCONF command groups")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RestconfCog(bot))
