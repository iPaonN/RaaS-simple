"""Background worker that consumes router task events from RabbitMQ."""
from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from pathlib import Path
from typing import Any, Optional

import sys

import aio_pika
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore[import]

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import settings
from domain.entities.task import Task, TaskStatus
from domain.services.task_service import TaskService
from infrastructure.mongodb.repositories import MongoTaskRepository
from infrastructure.mongodb.router_store import MongoRouterStore
from netmiko_client import ConfigService
from restconf.client import RestconfClient
from restconf.service import RestconfService
from utils.logger import configure_logging, get_logger

configure_logging(settings.LOG_LEVEL)
_logger = get_logger(__name__)

_mongo_client: AsyncIOMotorClient | None = None
_task_service: TaskService | None = None
_router_store: MongoRouterStore | None = None


async def _ensure_dependencies() -> None:
    global _mongo_client, _task_service, _router_store

    if _mongo_client and _task_service and _router_store:
        return

    if not settings.MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not configured; worker cannot start")

    _mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
    database = _mongo_client[settings.MONGODB_DB]

    task_repository = MongoTaskRepository(database[settings.MONGODB_TASK_COLLECTION])
    _task_service = TaskService(task_repository)
    _router_store = MongoRouterStore(database[settings.MONGODB_ROUTER_COLLECTION])
    _logger.info("MongoDB connections initialised for worker")


async def _handle_event(envelope: dict[str, Any]) -> None:
    await _ensure_dependencies()

    event_type = envelope.get("event")
    payload = envelope.get("payload") or {}

    if event_type == "task.router.backup":
        await _process_backup_task(payload)
    elif event_type == "task.router.health":
        await _process_health_task(payload)
    else:  # pragma: no cover - future event types
        _logger.info("Ignoring unsupported event type: %s", event_type)


async def _process_backup_task(payload: dict[str, Any]) -> None:
    if _task_service is None or _router_store is None:
        raise RuntimeError("Task dependencies not initialised")

    task_id: Optional[str] = payload.get("task_id")
    router_ip: Optional[str] = payload.get("router_ip")
    guild_id: Optional[int] = payload.get("guild_id")
    channel_id: Optional[int] = payload.get("channel_id")
    user_id: Optional[int] = payload.get("user_id")

    if not task_id or not router_ip:
        _logger.error("Received malformed backup payload: %s", payload)
        return

    task: Task | None = await _task_service.get(task_id)
    if task is None:
        _logger.error("Task %s not found in repository", task_id)
        return

    task = await _task_service.mark_running(task)

    try:
        if guild_id is None:
            raise RuntimeError("Guild identifier missing for backup task")

        router_doc = await _router_store.get_router(guild_id, router_ip)
        if router_doc is None:
            raise RuntimeError(f"Router credentials not found for {router_ip}")

        username = router_doc.get("username")
        password = router_doc.get("password")
        if not username or not password:
            raise RuntimeError("Stored router credentials are incomplete")

        label = task.metadata.get("router_label") or router_doc.get("name") or router_doc.get("hostname") or router_ip
        config_service = ConfigService(router_ip, username, password)
        config_path = await config_service.get_running_config()

        task.metadata["router_label"] = str(label)
        task.metadata["config_path"] = str(config_path)
        note = task.metadata.get("note")

        task = await _task_service.mark_completed(task, f"Configuration archived as {Path(config_path).name}")
        _logger.info(
            "Backup task %s completed for %s", task.id, task.router_host
        )

        await _notify_discord(
            channel_id=channel_id,
            user_id=user_id,
            task=task,
            file_path=config_path,
            note=str(note) if note else None,
        )
    except Exception as exc:
        error_message = str(exc)
        task.metadata["error"] = error_message
        task = await _task_service.mark_failed(task, error_message)
        await _notify_discord(
            channel_id=channel_id,
            user_id=user_id,
            task=task,
            file_path=None,
            note=None,
        )
        _logger.error("Backup task %s failed: %s", task_id, exc)


async def _process_health_task(payload: dict[str, Any]) -> None:
    if _task_service is None or _router_store is None:
        raise RuntimeError("Task dependencies not initialised")

    task_id: Optional[str] = payload.get("task_id")
    router_ip: Optional[str] = payload.get("router_ip")
    guild_id: Optional[int] = payload.get("guild_id")

    if not task_id or not router_ip or guild_id is None:
        _logger.error("Received malformed health payload: %s", payload)
        return

    task: Task | None = await _task_service.get(task_id)
    if task is None:
        _logger.error("Task %s not found in repository", task_id)
        return

    task = await _task_service.mark_running(task)

    try:
        router_doc = await _router_store.get_router(guild_id, router_ip)
        if router_doc is None:
            raise RuntimeError(f"Router credentials not found for {router_ip}")

        username = router_doc.get("username")
        password = router_doc.get("password")
        if not username or not password:
            raise RuntimeError("Stored router credentials are incomplete")

        client = RestconfClient(router_ip, username, password, timeout=20.0)
        service = RestconfService(client)

        hostname_obj = await service.fetch_hostname()
        interfaces = await service.fetch_interfaces()
        try:
            routing_table = await service.fetch_routing_table()
            static_route_count = len(routing_table.static_routes)
        except Exception as exc:  # pragma: no cover - optional data path
            static_route_count = None
            _logger.warning("Failed to fetch routing table for %s: %s", router_ip, exc)

        enabled_interfaces = sum(1 for iface in interfaces if iface.enabled)
        summary_lines = [
            f"Hostname: {hostname_obj.value}",
            f"Interfaces: {len(interfaces)} total / {enabled_interfaces} up / {len(interfaces) - enabled_interfaces} down",
        ]
        if static_route_count is None:
            summary_lines.append("Static Routes: unavailable")
        else:
            summary_lines.append(f"Static Routes: {static_route_count}")

        task.metadata["router_label"] = task.metadata.get("router_label") or hostname_obj.value or router_ip
        task.metadata["health"] = {
            "hostname": hostname_obj.value,
            "interfaces_total": len(interfaces),
            "interfaces_up": enabled_interfaces,
            "interfaces_down": len(interfaces) - enabled_interfaces,
            "static_routes": static_route_count,
        }

        task = await _task_service.mark_completed(task, "\n".join(summary_lines))
        _logger.info("Health task %s completed for %s", task.id, task.router_host)
    except Exception as exc:
        error_message = str(exc)
        task.metadata["error"] = error_message
        task = await _task_service.mark_failed(task, error_message)
        _logger.error("Health task %s failed: %s", task_id, exc)


async def _notify_discord(
    *,
    channel_id: Optional[int],
    user_id: Optional[int],
    task: Task,
    file_path: Optional[Path],
    note: Optional[str],
) -> None:
    token = settings.TOKEN
    if channel_id is None or not token:
        if not token:
            _logger.warning("DISCORD_TOKEN not configured; skipping notification for task %s", task.id)
        return

    mention = f"<@{user_id}> " if user_id else ""
    router_label = task.metadata.get("router_label") or task.router_host

    if task.status == TaskStatus.COMPLETED:
        base_message = f"✅ {mention}Backup task `{task.id}` for **{router_label}** completed."
        if note:
            base_message += f"\n📝 Note: {note}"
        content = base_message
    else:
        content = (
            f"❌ {mention}Backup task `{task.id}` for **{router_label}** failed.\n"
            f"Error: {task.result}"
        )

    headers = {"Authorization": f"Bot {token}"}
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"

    async with aiohttp.ClientSession() as session:
        if file_path and file_path.exists():
            with file_path.open("rb") as file_obj:
                form = aiohttp.FormData()
                form.add_field(
                    "payload_json",
                    json.dumps({"content": content}),
                    content_type="application/json",
                )
                form.add_field(
                    "files[0]",
                    file_obj,
                    filename=file_path.name,
                    content_type="text/plain",
                )
                async with session.post(url, headers=headers, data=form) as response:
                    if response.status >= 400:
                        body = await response.text()
                        _logger.error("Discord upload failed (%s): %s", response.status, body)
        else:
            async with session.post(url, headers=headers, json={"content": content}) as response:
                if response.status >= 400:
                    body = await response.text()
                    _logger.error("Discord notification failed (%s): %s", response.status, body)


async def _consume() -> None:
    if not settings.RABBITMQ_URI:
        raise RuntimeError("RABBITMQ_URI is not configured; worker cannot start")

    queue_name = settings.RABBITMQ_TASK_QUEUE or "router_tasks"

    _logger.info("Connecting to RabbitMQ at %s", settings.RABBITMQ_URI)
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URI)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=5)

        queue = await channel.declare_queue(queue_name, durable=True)
        _logger.info("Listening for router tasks on queue: %s", queue_name)

        async with queue.iterator() as iterator:
            async for message in iterator:
                async with message.process():
                    try:
                        envelope = json.loads(message.body)
                    except json.JSONDecodeError:
                        _logger.error("Received malformed message: %s", message.body)
                        continue

                    await _handle_event(envelope)


async def _shutdown_dependencies() -> None:
    global _mongo_client

    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        _logger.info("MongoDB connection closed for worker")


async def main() -> None:
    backoff = 5
    try:
        while True:
            try:
                await _consume()
            except asyncio.CancelledError:  # pragma: no cover - cancellation path
                raise
            except Exception as exc:  # pragma: no cover - resiliency loop
                _logger.error("Worker error: %s", exc)
                _logger.info("Retrying connection in %s seconds", backoff)
                await asyncio.sleep(backoff)
    finally:
        await _shutdown_dependencies()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())