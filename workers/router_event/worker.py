"""Background worker that consumes router task events from RabbitMQ."""
from __future__ import annotations

import asyncio
import json
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any, Awaitable, Callable

import aio_pika

# Ensure project root is importable when executed as a script
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from config import settings
from utils.logger import configure_logging, get_logger
from workers.router_event.backup import process_backup_task
from workers.router_event.dependencies import (
    WorkerDependencies,
    ensure_dependencies,
    shutdown_dependencies,
)
from workers.router_event.health import process_health_task
from workers.router_event.notifications import notify_discord

configure_logging(settings.LOG_LEVEL)
_logger = get_logger(__name__)

EventHandler = Callable[[dict[str, Any], WorkerDependencies], Awaitable[None]]


async def _dispatch_backup(payload: dict[str, Any], deps: WorkerDependencies) -> None:
    await process_backup_task(payload, deps, notify_discord)


_EVENT_HANDLERS: dict[str, EventHandler] = {
    "task.router.backup": _dispatch_backup,
    "task.router.health": process_health_task,
}


async def _handle_event(envelope: dict[str, Any]) -> None:
    deps = await ensure_dependencies()

    event_type = envelope.get("event")
    payload = envelope.get("payload") or {}

    handler = _EVENT_HANDLERS.get(event_type)
    if handler is None:  # pragma: no cover - future event types
        _logger.info("Ignoring unsupported event type: %s", event_type)
        return

    await handler(payload, deps)


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
        await shutdown_dependencies()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
