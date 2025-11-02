"""Task repository interface."""

from __future__ import annotations

from typing import Protocol

from domain.entities.task import Task


class TaskRepository(Protocol):
    """Abstract persistence layer for task entities."""

    async def add(self, task: Task) -> Task:
        ...

    async def list(self) -> list[Task]:
        ...

    async def get(self, task_id: str) -> Task | None:
        ...

    async def update(self, task: Task) -> Task:
        ...
