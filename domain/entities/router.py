"""Router domain entity definition."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class Router:
    """Represents a manageable network router."""

    name: str
    host: str
    username: str
    password: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    description: Optional[str] = None
