"""Dependency management for the router event worker."""
from __future__ import annotations

from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore[import]

from config import settings
from domain.services.task_service import TaskService
from infrastructure.mongodb.repositories import MongoTaskRepository
from infrastructure.mongodb.router_store import MongoRouterStore
from utils.logger import get_logger

_logger = get_logger(__name__)


def _build_task_service(database) -> TaskService:
    task_collection = database[settings.MONGODB_TASK_COLLECTION]
    task_repository = MongoTaskRepository(task_collection)
    return TaskService(task_repository)


def _build_router_store(database) -> MongoRouterStore:
    router_collection = database[settings.MONGODB_ROUTER_COLLECTION]
    return MongoRouterStore(router_collection)


@dataclass
class WorkerDependencies:
    """Runtime services used by the worker loop."""

    mongo_client: AsyncIOMotorClient | None = None
    task_service: TaskService | None = None
    router_store: MongoRouterStore | None = None


_dependencies = WorkerDependencies()


async def ensure_dependencies() -> WorkerDependencies:
    """Initialise (if required) and return worker dependencies."""

    if _dependencies.mongo_client and _dependencies.task_service and _dependencies.router_store:
        return _dependencies

    if not settings.MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not configured; worker cannot start")

    if _dependencies.mongo_client is None:
        _dependencies.mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
        _logger.info("MongoDB client connected for worker")

    database = _dependencies.mongo_client[settings.MONGODB_DB]

    if _dependencies.task_service is None:
        _dependencies.task_service = _build_task_service(database)

    if _dependencies.router_store is None:
        _dependencies.router_store = _build_router_store(database)

    return _dependencies


async def shutdown_dependencies() -> None:
    """Release resources held by the worker dependencies."""

    if _dependencies.mongo_client is not None:
        _dependencies.mongo_client.close()
        _logger.info("MongoDB connection closed for worker")

    _dependencies.mongo_client = None
    _dependencies.task_service = None
    _dependencies.router_store = None
