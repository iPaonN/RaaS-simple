"""Dependency management for the router monitor worker."""
from __future__ import annotations

from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore[import]

from config import settings
from infrastructure.mongodb.router_store import MongoRouterStore
from utils.logger import get_logger

_logger = get_logger(__name__)


@dataclass
class MonitorDependencies:
    """Container for services reused across monitor iterations."""

    mongo_client: AsyncIOMotorClient | None = None
    router_store: MongoRouterStore | None = None


_dependencies = MonitorDependencies()


async def ensure_dependencies() -> MonitorDependencies:
    """Initialise (if necessary) and return worker dependencies."""

    if _dependencies.mongo_client and _dependencies.router_store:
        return _dependencies

    if not settings.MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not configured; router monitor cannot start")

    if _dependencies.mongo_client is None:
        _dependencies.mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
        _logger.info("MongoDB client connected for router monitor")

    database = _dependencies.mongo_client[settings.MONGODB_DB]
    _dependencies.router_store = MongoRouterStore(database[settings.MONGODB_ROUTER_COLLECTION])
    return _dependencies


async def shutdown_dependencies() -> None:
    """Dispose of shared resources."""

    if _dependencies.mongo_client is not None:
        _dependencies.mongo_client.close()
        _logger.info("MongoDB client closed for router monitor")

    _dependencies.mongo_client = None
    _dependencies.router_store = None
