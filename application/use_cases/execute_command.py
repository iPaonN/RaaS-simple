"""Use case for executing RESTCONF commands asynchronously."""

from __future__ import annotations

from domain.entities.task import Task
from domain.services.task_service import TaskService


class ExecuteCommandUseCase:
    """Queue command execution and update task lifecycle."""

    def __init__(self, task_service: TaskService) -> None:
        self._task_service = task_service

    async def execute(self, task: Task) -> Task:
        return await self._task_service.queue_task(task)
