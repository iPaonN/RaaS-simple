"""Command group registration for configuration operations."""
from __future__ import annotations

from typing import Optional, Sequence

from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.command_groups.config_shared import ConfigServiceBuilder
from restconf.connection_manager import ConnectionManager
from netmiko_client import ConfigService

from .config_backup import build_backup_command
from .config_get import build_get_config_command


class ConfigCommandGroup(CommandGroup):
    """Factory for the configuration command group referencing modular builders."""

    def __init__(
        self,
        connection_manager: ConnectionManager,
        service_builder: Optional[ConfigServiceBuilder] = None,
    ) -> None:
        resolved_builder = service_builder or ConfigService
        commands: Sequence[app_commands.Command] = [
            build_get_config_command(connection_manager, resolved_builder),
            build_backup_command(connection_manager, resolved_builder),
        ]
        super().__init__(commands)
