"""RabbitMQ message publisher implementation."""

from __future__ import annotations

from typing import Any

import aio_pika  # type: ignore[import]


class RabbitMQPublisher:
    """Simple publisher that sends messages to a topic exchange."""

    def __init__(self, channel: aio_pika.abc.AbstractChannel, exchange_name: str) -> None:
        self._channel = channel
        self._exchange_name = exchange_name

    async def publish(self, routing_key: str, payload: bytes, **kwargs: Any) -> None:
        exchange = await self._channel.declare_exchange(self._exchange_name, aio_pika.ExchangeType.TOPIC)
        message = aio_pika.Message(body=payload, headers=kwargs.get("headers"))
        await exchange.publish(message, routing_key=routing_key)
