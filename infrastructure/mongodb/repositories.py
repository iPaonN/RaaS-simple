"""MongoDB repository implementations."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from domain.entities.router import Router
from domain.entities.task import Task
from domain.repositories.router_repository import RouterRepository
from domain.repositories.task_repository import TaskRepository


class MongoRouterRepository(RouterRepository):
    """Router repository backed by MongoDB collections."""

    def __init__(self, collection) -> None:  # pragma: no cover - wiring only
        self._collection = collection

    async def add(self, router: Router) -> Router:
        await self._collection.insert_one(asdict(router))
        return router

    async def list(self) -> list[Router]:
        docs: list[Router] = []
        async for document in self._collection.find():
            docs.append(Router(**{k: v for k, v in document.items() if k != "_id"}))
        return docs

    async def get_by_host(self, host: str) -> Router | None:
        document = await self._collection.find_one({"host": host})
        if not document:
            return None
        return Router(**{k: v for k, v in document.items() if k != "_id"})


class MongoTaskRepository(TaskRepository):
    """Task repository backed by MongoDB collections."""

    def __init__(self, collection) -> None:  # pragma: no cover - wiring only
        self._collection = collection

    async def add(self, task: Task) -> Task:
        await self._collection.insert_one(asdict(task))
        return task

    async def list(self) -> list[Task]:
        tasks: list[Task] = []
        async for document in self._collection.find():
            tasks.append(self._deserialize(document))
        return tasks

    async def get(self, task_id: str) -> Task | None:
        document = await self._collection.find_one({"id": task_id})
        return self._deserialize(document) if document else None

    async def update(self, task: Task) -> Task:
        await self._collection.replace_one({"id": task.id}, asdict(task), upsert=True)
        return task

    @staticmethod
    def _deserialize(document: dict[str, Any]) -> Task:
        cleaned = {k: v for k, v in document.items() if k != "_id"}
        if "type" not in cleaned:
            cleaned["type"] = cleaned.get("command", "task")
        metadata = cleaned.get("metadata")
        if not isinstance(metadata, dict):
            cleaned["metadata"] = {}
        return Task(**cleaned)
