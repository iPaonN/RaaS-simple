"""Shared helpers for RESTCONF task command builders."""
from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands

from domain.entities.task import TaskStatus
from domain.services.task_service import TaskService
from infrastructure.mongodb.router_store import MongoRouterStore
from utils.embeds import create_error_embed
from utils.logger import get_logger

_logger = get_logger(__name__)


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
