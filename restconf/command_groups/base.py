"""Base class for RESTCONF command groups."""
from __future__ import annotations

from typing import Iterable, List

from discord import app_commands


class CommandGroup:
    """Utility wrapper to register/unregister a set of commands."""

    def __init__(self, commands: Iterable[app_commands.Command]) -> None:
        self._commands: List[app_commands.Command] = list(commands)

    def register(self, tree: app_commands.CommandTree) -> None:
        for command in self._commands:
            tree.add_command(command)

    def unregister(self, tree: app_commands.CommandTree) -> None:
        for command in self._commands:
            tree.remove_command(command.name, type=command.type)
