"""Command group registration for device configuration commands."""
from __future__ import annotations

from typing import Sequence

from discord import app_commands

from restconf.command_groups.base import CommandGroup
from restconf.command_groups.device_shared import ServiceBuilder
from restconf.connection_manager import ConnectionManager

from .device_banner import build_get_banner_motd_command, build_set_banner_motd_command
from .device_domain import build_get_domain_name_command, build_set_domain_name_command
from .device_hostname import build_get_hostname_command, build_set_hostname_command
from .device_name_servers import build_get_name_servers_command
from .device_save_config import build_save_config_command


class DeviceCommandGroup(CommandGroup):
    """Factory for the device command group referencing modular builders."""

    def __init__(self, service_builder: ServiceBuilder, connection_manager: ConnectionManager) -> None:
        commands: Sequence[app_commands.Command] = [
            build_get_hostname_command(service_builder, connection_manager),
            build_set_hostname_command(service_builder, connection_manager),
            build_get_banner_motd_command(service_builder, connection_manager),
            build_set_banner_motd_command(service_builder, connection_manager),
            build_get_domain_name_command(service_builder, connection_manager),
            build_set_domain_name_command(service_builder, connection_manager),
            build_get_name_servers_command(service_builder, connection_manager),
            build_save_config_command(service_builder, connection_manager),
        ]
        super().__init__(commands)