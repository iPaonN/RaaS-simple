"""Command builder for queuing router configuration backups."""
from __future__ import annotations

from typing import Optional
from uuid import uuid4

import discord
from discord import app_commands

from domain.entities.task import Task
from domain.services.task_service import TaskService
from infrastructure.mongodb.router_store import MongoRouterStore
from utils.embeds import create_error_embed, create_success_embed
from utils.logger import get_logger

from .task_shared import (
    build_router_choices,
    select_router_by_identifier,
)

_logger = get_logger(__name__)


def build_backup_command(
    router_store: Optional[MongoRouterStore],
    task_service: Optional[TaskService],
) -> app_commands.Command:
    """Create the `/backup-config` command definition."""

    @app_commands.command(
        name="backup-config",
        description="Queue a configuration backup task for a stored router",
    )
    @app_commands.describe(
        router="Router IP or name from your stored list",
        note="Optional note to include with the task",
    )
    async def command(
        interaction: discord.Interaction,
        router: str,
        note: Optional[str] = None,
    ) -> None:
        await interaction.response.defer(thinking=True)

        # RabbitMQ has been removed - this feature is not available
        await interaction.followup.send(
            embed=create_error_embed(
                title="❌ Feature Not Available",
                description=(
                    "Background task processing requires RabbitMQ, which has been disabled.\n\n"
                    "You can still use `/get-config` for immediate configuration downloads."
                ),
            ),
            ephemeral=True,
        )
        return

    @command.autocomplete("router")
    async def router_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current_router_store = router_store or getattr(interaction.client, "router_store", None)
        return await build_router_choices(current_router_store, interaction.guild_id, current)

    return command
