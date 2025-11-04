"""Connection command group aggregator with per-command modules."""
from __future__ import annotations

from typing import Optional, Sequence

from discord import app_commands

from infrastructure.mongodb.router_store import MongoRouterStore
from restconf.command_groups.base import CommandGroup
from restconf.connection_manager import ConnectionManager
from restconf.services.connection import ConnectionService

from .connection_connect import build_connect_command
from .connection_disconnect import build_disconnect_command
from .connection_router_list import build_router_list_command


class ConnectionCommandGroup(CommandGroup):
    """Factory for the connection command group with modular command builders."""

    def __init__(
        self,
        connection_manager: ConnectionManager,
        connection_service: ConnectionService,
        router_store: Optional[MongoRouterStore] = None,
    ) -> None:
        commands: Sequence[app_commands.Command] = [
            build_connect_command(connection_manager, connection_service, router_store),
            build_disconnect_command(connection_service),
            build_router_list_command(connection_manager, connection_service, router_store),
        ]
        super().__init__(commands)
