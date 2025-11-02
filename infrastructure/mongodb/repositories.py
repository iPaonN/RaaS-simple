"""MongoDB repository implementations."""

from __future__ import annotations

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
        await self._collection.insert_one(router.__dict__)
        return router

    async def list(self) -> list[Router]:
        docs: list[Router] = []
        async for document in self._collection.find():
            docs.append(Router(**document))
        return docs

    async def get_by_host(self, host: str) -> Router | None:
        document = await self._collection.find_one({"host": host})
        return Router(**document) if document else None


class MongoTaskRepository(TaskRepository):
    """Task repository backed by MongoDB collections."""

    def __init__(self, collection) -> None:  # pragma: no cover - wiring only
        self._collection = collection

    async def add(self, task: Task) -> Task:
        await self._collection.insert_one(task.__dict__)
        return task

    async def list(self) -> list[Task]:
        tasks: list[Task] = []
        async for document in self._collection.find():
            tasks.append(Task(**document))
        return tasks

    async def get(self, task_id: str) -> Task | None:
        document = await self._collection.find_one({"id": task_id})
        return Task(**document) if document else None

    async def update(self, task: Task) -> Task:
        await self._collection.replace_one({"id": task.id}, task.__dict__, upsert=True)
        return task
