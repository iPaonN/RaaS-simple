"""Task handler that invokes application use cases."""

from __future__ import annotations

from application.use_cases.execute_command import ExecuteCommandUseCase
from domain.entities.task import Task


class TaskHandler:
    """Coordinates execution of queued tasks."""

    def __init__(self, execute_command: ExecuteCommandUseCase) -> None:
        self._execute_command = execute_command

    async def handle(self, task: Task) -> Task:
        return await self._execute_command.execute(task)
