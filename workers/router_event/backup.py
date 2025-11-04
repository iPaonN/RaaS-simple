"""Backup task handler for the router event worker."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from netmiko_client import ConfigService

from .dependencies import WorkerDependencies
from .helpers import load_router_credentials
from utils.logger import get_logger

_logger = get_logger(__name__)

NotifyFunc = Callable[..., Awaitable[None]]


async def process_backup_task(
    payload: dict[str, Any],
    deps: WorkerDependencies,
    notify_discord: NotifyFunc,
) -> None:
    """Handle a router configuration backup task."""

    task_service = deps.task_service
    router_store = deps.router_store
    if task_service is None or router_store is None:
        raise RuntimeError("Task dependencies not initialised")

    task_id: Optional[str] = payload.get("task_id")
    router_ip: Optional[str] = payload.get("router_ip")
    guild_id: Optional[int] = payload.get("guild_id")
    channel_id: Optional[int] = payload.get("channel_id")
    user_id: Optional[int] = payload.get("user_id")

    if not task_id or not router_ip:
        _logger.error("Received malformed backup payload: %s", payload)
        return

    task = await task_service.get(task_id)
    if task is None:
        _logger.error("Task %s not found in repository", task_id)
        return

    task = await task_service.mark_running(task)
    metadata = task.metadata or {}
    task.metadata = metadata

    try:
        if guild_id is None:
            raise RuntimeError("Guild identifier missing for backup task")

        router_doc, username, password = await load_router_credentials(router_store, guild_id, router_ip)

        label = (
            metadata.get("router_label")
            or router_doc.get("name")
            or router_doc.get("hostname")
            or router_ip
        )
        config_service = ConfigService(router_ip, username, password)
        config_path = await config_service.get_running_config()

        metadata["router_label"] = str(label)
        metadata["config_path"] = str(config_path)
        note = metadata.get("note")

        task = await task_service.mark_completed(
            task, f"Configuration archived as {Path(config_path).name}"
        )
        _logger.info("Backup task %s completed for %s", task.id, task.router_host)

        await notify_discord(
            channel_id=channel_id,
            user_id=user_id,
            task=task,
            file_path=config_path,
            note=str(note) if note else None,
        )
    except Exception as exc:
        error_message = str(exc)
        metadata["error"] = error_message
        task = await task_service.mark_failed(task, error_message)
        await notify_discord(
            channel_id=channel_id,
            user_id=user_id,
            task=task,
            file_path=None,
            note=None,
        )
        _logger.error("Backup task %s failed: %s", task_id, exc)
