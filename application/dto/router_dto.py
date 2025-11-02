"""DTO definitions for routers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RouterDTO:
    """Serializable router representation exposed to the UI layer."""

    name: str
    host: str
    description: str | None = None
