"""Task domain entity definition."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any


class TaskStatus(str, Enum):
    """High-level lifecycle for automation tasks."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class Task:
    """Represents a queued automation task."""

    id: str
    type: str
    router_host: str
    command: str
    guild_id: Optional[int] = None
    channel_id: Optional[int] = None
    user_id: Optional[int] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
