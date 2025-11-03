"""RabbitMQ helper for publishing asynchronous router events."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

import aio_pika

from utils.logger import get_logger

_logger = get_logger(__name__)


class RabbitMQClient:
    """Lightweight wrapper around aio-pika for publishing events."""

    def __init__(self, uri: str, queue_name: str) -> None:
        self._uri = uri
        self._queue_name = queue_name
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._queue: Optional[aio_pika.abc.AbstractQueue] = None
        self._queues: dict[str, aio_pika.abc.AbstractQueue] = {}

    async def connect(self) -> None:
        """Establish a connection and declare the queue if needed."""

        _logger.info("Connecting to RabbitMQ (queue=%s)", self._queue_name)
        self._connection = await aio_pika.connect_robust(self._uri)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)
        self._queue = await self._channel.declare_queue(
            self._queue_name,
            durable=True,
        )
        self._queues[self._queue_name] = self._queue
        _logger.info("RabbitMQ connection established")

    async def publish_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        queue_name: Optional[str] = None,
    ) -> None:
        """Publish an event message to the configured queue."""

        if self._channel is None:
            raise RuntimeError("RabbitMQ channel not initialised")

        envelope = {
            "event": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        body = json.dumps(envelope).encode("utf-8")
        message = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        target_queue = await self._resolve_queue(queue_name or self._queue_name)
        await self._channel.default_exchange.publish(
            message,
            routing_key=target_queue.name,
        )
        _logger.debug("Published RabbitMQ event %s to %s", event_type, target_queue.name)

    async def close(self) -> None:
        """Close the connection and channel gracefully."""

        try:
            if self._channel and not self._channel.is_closed:
                await self._channel.close()
        finally:
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
        _logger.info("RabbitMQ connection closed")

    async def _resolve_queue(self, queue_name: str) -> aio_pika.abc.AbstractQueue:
        if self._channel is None:
            raise RuntimeError("RabbitMQ channel not initialised")

        if queue_name in self._queues:
            return self._queues[queue_name]

        queue = await self._channel.declare_queue(queue_name, durable=True)
        self._queues[queue_name] = queue
        return queue