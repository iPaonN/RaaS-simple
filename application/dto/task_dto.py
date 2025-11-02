"""DTO definitions for automation tasks."""

from __future__ import annotations

from dataclasses import dataclass

from domain.entities.task import TaskStatus


@dataclass(slots=True)
class TaskDTO:
    """Serializable task representation exposed to the UI layer."""

    id: str
    router_host: str
    command: str
    status: TaskStatus
    result: str | None = None
