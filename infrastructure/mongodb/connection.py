"""MongoDB connection helpers."""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore[import]


class MongoConnectionFactory:
    """Factory responsible for creating MongoDB client instances."""

    def __init__(self, uri: str, **kwargs: Any) -> None:
        self._uri = uri
        self._kwargs = kwargs

    def create_client(self) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(self._uri, **self._kwargs)
