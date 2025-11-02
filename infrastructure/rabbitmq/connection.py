"""RabbitMQ connection helpers."""

from __future__ import annotations

import aio_pika  # type: ignore[import]


class RabbitMQConnectionFactory:
    """Factory responsible for producing aio-pika connections."""

    def __init__(self, url: str) -> None:
        self._url = url

    async def create_connection(self) -> aio_pika.RobustConnection:
        return await aio_pika.connect_robust(self._url)
