"""Shared helpers for RESTCONF task command builders."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import discord
from discord import app_commands

from domain.entities.task import TaskStatus
from domain.services.task_service import TaskService
from infrastructure.messaging.rabbitmq import RabbitMQClient
from infrastructure.mongodb.router_store import MongoRouterStore
from utils.embeds import create_error_embed
from utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass
class TaskDependencies:
    router_store: MongoRouterStore
    task_service: TaskService
    message_client: RabbitMQClient
    task_queue_name: str


async def build_router_choices(
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


async def build_task_choices(
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


def select_router_by_identifier(
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


async def resolve_task_dependencies(
    interaction: discord.Interaction,
    router_store: Optional[MongoRouterStore],
    task_service: Optional[TaskService],
    message_client: Optional[RabbitMQClient],
    task_queue_name: Optional[str],
) -> Optional[TaskDependencies]:
    """Resolve task dependencies from injected values or the bot instance."""

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
                description="MongoDB is required to queue router tasks.",
            ),
            ephemeral=True,
        )
        return None

    if current_task_service is None or current_message_client is None or not current_task_queue:
        await interaction.followup.send(
            embed=create_error_embed(
                title="❌ Task Queue Unavailable",
                description="RabbitMQ must be configured before tasks can be queued.",
            ),
            ephemeral=True,
        )
        return None

    if interaction.guild_id is None or interaction.channel_id is None:
        await interaction.followup.send(
            embed=create_error_embed(
                title="❌ Server Only",
                description="This command is only available inside a Discord server channel.",
            ),
            ephemeral=True,
        )
        return None

    return TaskDependencies(
        router_store=current_router_store,
        task_service=current_task_service,
        message_client=current_message_client,
        task_queue_name=current_task_queue,
    )
