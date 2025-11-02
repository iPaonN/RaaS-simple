"""Queue abstraction interfaces used by task execution."""

from __future__ import annotations

from typing import Protocol


class MessageQueue(Protocol):
    """Basic contract for publishing and consuming messages."""

    async def publish(self, routing_key: str, payload: bytes) -> None:
        ...

    async def consume(self, queue_name: str) -> bytes:
        ...
