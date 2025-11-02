"""RabbitMQ message consumer implementation."""

from __future__ import annotations

from typing import Awaitable, Callable

import aio_pika  # type: ignore[import]

MessageHandler = Callable[[aio_pika.IncomingMessage], Awaitable[None]]


class RabbitMQConsumer:
    """Consumes messages from a queue and dispatches to a handler."""

    def __init__(self, channel: aio_pika.abc.AbstractChannel, queue_name: str) -> None:
        self._channel = channel
        self._queue_name = queue_name

    async def start(self, handler: MessageHandler) -> aio_pika.abc.AbstractQueue:
        queue = await self._channel.declare_queue(self._queue_name, durable=True)
        await queue.consume(handler)
        return queue
