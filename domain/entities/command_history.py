"""Command history entity tracking execution metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence


@dataclass(slots=True)
class CommandHistory:
    """Captures a sequence of commands executed against a router."""

    router_host: str
    commands: Sequence[str]
    executed_at: datetime = field(default_factory=datetime.utcnow)
    executed_by: str | None = None
