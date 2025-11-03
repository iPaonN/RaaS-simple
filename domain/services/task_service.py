"""Business logic for automation tasks."""

from __future__ import annotations

from datetime import datetime

from domain.entities.task import Task, TaskStatus
from domain.repositories.task_repository import TaskRepository


class TaskService:
    """Handles task lifecycle transitions and reporting."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def queue_task(self, task: Task) -> Task:
        task.status = TaskStatus.PENDING
        task.created_at = datetime.utcnow()
        task.updated_at = task.created_at
        return await self._repository.add(task)

    async def mark_running(self, task: Task) -> Task:
        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.utcnow()
        return await self._repository.update(task)

    async def mark_completed(self, task: Task, result: str) -> Task:
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.updated_at = datetime.utcnow()
        return await self._repository.update(task)

    async def mark_failed(self, task: Task, error: str) -> Task:
        task.status = TaskStatus.FAILED
        task.result = error
        task.updated_at = datetime.utcnow()
        return await self._repository.update(task)

    async def get(self, task_id: str) -> Task | None:
        return await self._repository.get(task_id)
