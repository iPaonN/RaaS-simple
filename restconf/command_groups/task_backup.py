"""Command builder for queuing router configuration backups."""
from __future__ import annotations

from typing import Optional
from uuid import uuid4

import discord
from discord import app_commands

from domain.entities.task import Task
from domain.services.task_service import TaskService
from infrastructure.messaging.rabbitmq import RabbitMQClient
from infrastructure.mongodb.router_store import MongoRouterStore
from utils.embeds import create_error_embed, create_success_embed
from utils.logger import get_logger

from .task_shared import (
    TaskDependencies,
    build_router_choices,
    resolve_task_dependencies,
    select_router_by_identifier,
)

_logger = get_logger(__name__)


def build_backup_command(
    router_store: Optional[MongoRouterStore],
    task_service: Optional[TaskService],
    message_client: Optional[RabbitMQClient],
    task_queue_name: Optional[str],
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

        dependencies: Optional[TaskDependencies] = await resolve_task_dependencies(
            interaction,
            router_store,
            task_service,
            message_client,
            task_queue_name,
        )
        if dependencies is None:
            return

        note_text = note.strip() if note else None
        if note_text and len(note_text) > 200:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Note Too Long",
                    description="Please limit task notes to 200 characters.",
                ),
                ephemeral=True,
            )
            return

        try:
            routers = await dependencies.router_store.list_routers(interaction.guild_id)
        except Exception as exc:  # pragma: no cover - datastore error path
            _logger.error("Failed to list routers for guild %s: %s", interaction.guild_id, exc)
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Router Lookup Failed",
                    description="Could not retrieve stored routers. Please try again later.",
                ),
                ephemeral=True,
            )
            return

        router_doc = select_router_by_identifier(routers, router)
        if router_doc is None:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Router Not Found",
                    description=(
                        f"No stored router matched `{router}`. Use `/get-router-list` to review saved routers."
                    ),
                ),
                ephemeral=True,
            )
            return

        router_ip = router_doc.get("ip")
        router_username = router_doc.get("username")
        router_password = router_doc.get("password")
        if not router_ip or not router_username or not router_password:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Incomplete Router Profile",
                    description="The selected router does not have credentials saved for backups.",
                ),
                ephemeral=True,
            )
            return

        label = str(router_doc.get("name") or router_doc.get("hostname") or router_ip)
        metadata: dict[str, str] = {"router_label": label}
        if note_text:
            metadata["note"] = note_text

        task = Task(
            id=str(uuid4()),
            type="router.backup",
            router_host=str(router_ip),
            command="backup-config",
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
            metadata=metadata,
        )

        try:
            queued_task = await dependencies.task_service.queue_task(task)
        except Exception as exc:  # pragma: no cover - datastore error path
            _logger.error("Failed to persist task %s: %s", task.id, exc)
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Task Queue Failed",
                    description="Unable to store the task. Please try again later.",
                ),
                ephemeral=True,
            )
            return

        payload = {
            "task_id": queued_task.id,
            "router_ip": queued_task.router_host,
            "guild_id": queued_task.guild_id,
            "channel_id": queued_task.channel_id,
            "user_id": queued_task.user_id,
        }

        try:
            await dependencies.message_client.publish_event(
                "task.router.backup",
                payload,
                queue_name=dependencies.task_queue_name,
            )
        except Exception as exc:  # pragma: no cover - messaging failure path
            _logger.error("Failed to publish backup task %s: %s", queued_task.id, exc)
            try:
                await dependencies.task_service.mark_failed(queued_task, "Queue dispatch failed")
            except Exception as mark_exc:  # pragma: no cover - best effort cleanup
                _logger.warning("Failed to mark task %s as failed: %s", queued_task.id, mark_exc)
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Task Dispatch Failed",
                    description="The task could not be sent to the worker queue. Please try again later.",
                ),
                ephemeral=True,
            )
            return

        embed = create_success_embed(
            title="✅ Backup Queued",
            description=(
                "Your request for **{label}** has been queued.\n"
                "Task ID: `{task_id}`\n\n"
                "You'll be notified when it's finished, or run `/task-status {task_id}` to check progress."
            ).format(label=label, task_id=queued_task.id),
        )
        await interaction.followup.send(embed=embed)

    @command.autocomplete("router")
    async def router_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current_router_store = router_store or getattr(interaction.client, "router_store", None)
        return await build_router_choices(current_router_store, interaction.guild_id, current)

    return command
