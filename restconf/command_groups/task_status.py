"""Command builder for querying task status."""
from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands

from domain.services.task_service import TaskService
from utils.embeds import create_error_embed, create_info_embed

from .task_shared import build_task_choices


def build_task_status_command(task_service: Optional[TaskService]) -> app_commands.Command:
    """Create the `/task-status` command definition."""

    @app_commands.command(name="task-status", description="Check the status of a queued router task")
    @app_commands.describe(task_id="Task identifier returned by the queue command")
    async def command(interaction: discord.Interaction, task_id: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        current_task_service = task_service or getattr(interaction.client, "task_service", None)
        if current_task_service is None:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Task Tracking Unavailable",
                    description="Task storage is not configured for this deployment.",
                ),
                ephemeral=True,
            )
            return

        task = await current_task_service.get(task_id)
        if task is None or (interaction.guild_id and task.guild_id and task.guild_id != interaction.guild_id):
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Task Not Found",
                    description="Could not find a task with that identifier for this server.",
                ),
                ephemeral=True,
            )
            return

        from domain.entities.task import TaskStatus  # local import to avoid top-level cycle

        status_emojis = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
        }
        emoji = status_emojis.get(task.status, "ℹ️")
        description_lines = [f"{emoji} **Status:** `{task.status}`"]
        if task.result:
            description_lines.append(f"📝 **Result:** {task.result}")
        if task.metadata.get("router_label"):
            description_lines.append(f"📡 **Router:** {task.metadata.get('router_label')}")
        if task.metadata.get("note"):
            description_lines.append(f"🗒️ **Note:** {task.metadata.get('note')}")

        embed = create_info_embed(
            title="Task Status",
            description="\n".join(description_lines),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @command.autocomplete("task_id")
    async def task_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current_task_service = task_service or getattr(interaction.client, "task_service", None)
        return await build_task_choices(current_task_service, interaction.guild_id, current)

    return command
