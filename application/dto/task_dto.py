"""DTO definitions for automation tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from domain.entities.task import Task, TaskStatus


@dataclass(slots=True)
class TaskDTO:
    """Transport-friendly representation of an automation task."""

    id: str
    router_host: str
    command: str
    status: TaskStatus
    result: str | None = None
    router_label: str | None = None
    note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    raw_metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_entity(cls, task: Task) -> "TaskDTO":
        """Build a DTO from the domain entity."""

        metadata = task.metadata or {}
        router_label = metadata.get("router_label")
        note = metadata.get("note")

        return cls(
            id=task.id,
            router_host=task.router_host,
            command=task.command,
            status=task.status,
            result=task.result,
            router_label=str(router_label) if router_label is not None else None,
            note=str(note) if note is not None else None,
            created_at=getattr(task, "created_at", None),
            updated_at=getattr(task, "updated_at", None),
            raw_metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary for responses."""

        return {
            "id": self.id,
            "router_host": self.router_host,
            "command": self.command,
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "result": self.result,
            "router_label": self.router_label,
            "note": self.note,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else None,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else None,
            "metadata": dict(self.raw_metadata),
        }
