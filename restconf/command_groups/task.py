"""Slash commands for managing asynchronous router tasks."""
from __future__ import annotations

from typing import Optional, Sequence
from uuid import uuid4

import discord
from discord import app_commands

from restconf.command_groups.base import CommandGroup
from infrastructure.messaging.rabbitmq import RabbitMQClient
from infrastructure.mongodb.router_store import MongoRouterStore
from domain.entities.task import Task, TaskStatus
from domain.services.task_service import TaskService
from utils.embeds import create_error_embed, create_info_embed, create_success_embed
from utils.logger import get_logger

_logger = get_logger(__name__)


async def _build_router_choices(
    router_store: Optional[MongoRouterStore],
    guild_id: Optional[int],
    current: str,
) -> list[app_commands.Choice[str]]:
    if router_store is None or guild_id is None:
        return []

    try:
        routers = await router_store.list_routers(guild_id)
    except Exception as exc:  # pragma: no cover - datastore error path
        _logger.warning(
            "Failed to load routers for autocomplete (guild=%s): %s",
            guild_id,
            exc,
        )
        return []

    normalized = current.lower()
    suggestions: list[app_commands.Choice[str]] = []
    for router_doc in routers:
        ip = router_doc.get("ip")
        label = router_doc.get("name") or router_doc.get("hostname") or ip
        if not ip or not label:
            continue
        candidate = str(label)
        if normalized and normalized not in candidate.lower() and normalized not in str(ip).lower():
            continue
        suggestions.append(app_commands.Choice(name=f"{candidate} ({ip})"[:100], value=str(ip)))
        if len(suggestions) >= 25:
            break

    return suggestions


async def _build_task_choices(
    task_service: Optional[TaskService],
    guild_id: Optional[int],
    current: str,
) -> list[app_commands.Choice[str]]:
    if task_service is None or guild_id is None:
        return []

    try:
        tasks = await task_service.list_tasks(guild_id=guild_id, limit=50)
    except Exception as exc:  # pragma: no cover - datastore error path
        _logger.warning(
            "Failed to load tasks for autocomplete (guild=%s): %s",
            guild_id,
            exc,
        )
        return []

    normalized = current.lower()
    choices: list[app_commands.Choice[str]] = []
    for task in tasks:
        task_id = task.id
        if not task_id:
            continue

        metadata = task.metadata or {}
        router_label = metadata.get("router_label")
        note = metadata.get("note")
        status_label = task.status.value if isinstance(task.status, TaskStatus) else str(task.status)

        descriptor_parts = [task.command]
        if router_label:
            descriptor_parts.append(str(router_label))
        descriptor_parts.append(status_label)
        if note:
            descriptor_parts.append(str(note))

        descriptor = " • ".join(part for part in descriptor_parts if part)
        search_blob = f"{task_id} {descriptor}".lower()
        if normalized and normalized not in search_blob:
            continue

        label = f"{task_id} | {descriptor}" if descriptor else task_id
        choices.append(app_commands.Choice(name=label[:100], value=task_id))
        if len(choices) >= 25:
            break

    return choices

def _select_router_by_identifier(
    routers: list[dict[str, object]],
    identifier: str,
) -> Optional[dict[str, object]]:
    normalized = identifier.lower()
    for router in routers:
        ip = str(router.get("ip", "")).lower()
        hostname = str(router.get("hostname", "")).lower()
        name = str(router.get("name", "")).lower()
        if normalized in {ip, hostname, name}:
            return router
    return None


def _build_backup_command(
    router_store: Optional[MongoRouterStore],
    task_service: Optional[TaskService],
    message_client: Optional[RabbitMQClient],
    task_queue_name: Optional[str],
) -> app_commands.Command:
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

        bot_instance = interaction.client
        current_router_store = router_store or getattr(bot_instance, "router_store", None)
        current_task_service = task_service or getattr(bot_instance, "task_service", None)
        current_message_client = message_client or getattr(bot_instance, "rabbitmq_client", None)
        current_task_queue = task_queue_name or getattr(bot_instance, "task_queue_name", None)

        ensure_rabbit = getattr(bot_instance, "ensure_rabbitmq", None)
        if callable(ensure_rabbit) and (current_message_client is None or not current_task_queue):
            if await ensure_rabbit():  # pragma: no cover - depends on runtime state
                current_task_service = current_task_service or getattr(bot_instance, "task_service", None)
                current_message_client = getattr(bot_instance, "rabbitmq_client", None)
                current_task_queue = getattr(bot_instance, "task_queue_name", None)

        if current_router_store is None:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Router Storage Unavailable",
                    description="MongoDB is required to queue backup tasks.",
                ),
                ephemeral=True,
            )
            return

        if current_task_service is None or current_message_client is None or not current_task_queue:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Task Queue Unavailable",
                    description="RabbitMQ must be configured before tasks can be queued.",
                ),
                ephemeral=True,
            )
            return

        if interaction.guild_id is None or interaction.channel_id is None:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Server Only",
                    description="This command is only available inside a Discord server channel.",
                ),
                ephemeral=True,
            )
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
            routers = await current_router_store.list_routers(interaction.guild_id)
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

        router_doc = _select_router_by_identifier(routers, router)
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
            queued_task = await current_task_service.queue_task(task)
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
            await current_message_client.publish_event(
                "task.router.backup",
                payload,
                queue_name=current_task_queue,
            )
        except Exception as exc:  # pragma: no cover - messaging failure path
            _logger.error("Failed to publish backup task %s: %s", queued_task.id, exc)
            try:
                await current_task_service.mark_failed(queued_task, "Queue dispatch failed")
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
        return await _build_router_choices(current_router_store, interaction.guild_id, current)

    return command


def _build_health_check_command(
    router_store: Optional[MongoRouterStore],
    task_service: Optional[TaskService],
    message_client: Optional[RabbitMQClient],
    task_queue_name: Optional[str],
) -> app_commands.Command:
    @app_commands.command(
        name="router-health",
        description="Queue a RESTCONF health check against a stored router",
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

        bot_instance = interaction.client
        current_router_store = router_store or getattr(bot_instance, "router_store", None)
        current_task_service = task_service or getattr(bot_instance, "task_service", None)
        current_message_client = message_client or getattr(bot_instance, "rabbitmq_client", None)
        current_task_queue = task_queue_name or getattr(bot_instance, "task_queue_name", None)

        ensure_rabbit = getattr(bot_instance, "ensure_rabbitmq", None)
        if callable(ensure_rabbit) and (current_message_client is None or not current_task_queue):
            if await ensure_rabbit():  # pragma: no cover - depends on runtime state
                current_task_service = current_task_service or getattr(bot_instance, "task_service", None)
                current_message_client = getattr(bot_instance, "rabbitmq_client", None)
                current_task_queue = getattr(bot_instance, "task_queue_name", None)

        if current_router_store is None:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Router Storage Unavailable",
                    description="MongoDB is required to queue health checks.",
                ),
                ephemeral=True,
            )
            return

        if current_task_service is None or current_message_client is None or not current_task_queue:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Task Queue Unavailable",
                    description="RabbitMQ must be configured before tasks can be queued.",
                ),
                ephemeral=True,
            )
            return

        if interaction.guild_id is None or interaction.channel_id is None:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Server Only",
                    description="This command is only available inside a Discord server channel.",
                ),
                ephemeral=True,
            )
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
            routers = await current_router_store.list_routers(interaction.guild_id)
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

        router_doc = _select_router_by_identifier(routers, router)
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
                    description="The selected router does not have credentials saved for health checks.",
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
            type="router.health",
            router_host=str(router_ip),
            command="router-health",
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
            metadata=metadata,
        )

        try:
            queued_task = await current_task_service.queue_task(task)
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
            await current_message_client.publish_event(
                "task.router.health",
                payload,
                queue_name=current_task_queue,
            )
        except Exception as exc:  # pragma: no cover - messaging failure path
            _logger.error("Failed to publish health task %s: %s", queued_task.id, exc)
            try:
                await current_task_service.mark_failed(queued_task, "Queue dispatch failed")
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
            title="✅ Health Check Queued",
            description=(
                "A health check for **{label}** has been queued.\n"
                "Task ID: `{task_id}`\n\n"
                "Run `/task-status {task_id}` to view the results once it's ready."
            ).format(label=label, task_id=queued_task.id),
        )
        await interaction.followup.send(embed=embed)

    @command.autocomplete("router")
    async def router_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current_router_store = router_store or getattr(interaction.client, "router_store", None)
        return await _build_router_choices(current_router_store, interaction.guild_id, current)

    return command


def _build_task_status_command(task_service: Optional[TaskService]) -> app_commands.Command:
    @app_commands.command(name="task-status", description="Check the status of a queued router task")
    @app_commands.describe(task_id="Task identifier returned by the queue command")
    async def command(interaction: discord.Interaction, task_id: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        if task_service is None:
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Task Tracking Unavailable",
                    description="Task storage is not configured for this deployment.",
                ),
                ephemeral=True,
            )
            return

        task = await task_service.get(task_id)
        if task is None or (interaction.guild_id and task.guild_id and task.guild_id != interaction.guild_id):
            await interaction.followup.send(
                embed=create_error_embed(
                    title="❌ Task Not Found",
                    description="Could not find a task with that identifier for this server.",
                ),
                ephemeral=True,
            )
            return

        status_emojis = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
        }
        emoji = status_emojis.get(task.status, "ℹ️")
        description_lines = [
            f"{emoji} **Status:** `{task.status}`",
        ]
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
        return await _build_task_choices(current_task_service, interaction.guild_id, current)

    return command


class TaskCommandGroup(CommandGroup):
    def __init__(
        self,
        router_store: Optional[MongoRouterStore],
        task_service: Optional[TaskService],
        message_client: Optional[RabbitMQClient],
        task_queue_name: Optional[str],
    ) -> None:
        commands: Sequence[app_commands.Command] = [
            _build_backup_command(
                router_store,
                task_service,
                message_client,
                task_queue_name,
            ),
            _build_health_check_command(
                router_store,
                task_service,
                message_client,
                task_queue_name,
            ),
            _build_task_status_command(task_service),
        ]
        super().__init__(commands)