"""RESTCONF-specific exception hierarchy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class RestconfError(Exception):
    """Base class for RESTCONF-related exceptions."""


class RestconfConnectionError(RestconfError):
    """Raised when the client cannot reach the target device."""

    def __init__(self, message: str, *, host: Optional[str] = None) -> None:
        self.host = host
        super().__init__(message)


@dataclass(slots=True)
class RestconfHTTPError(RestconfError):
    """Raised when the device returns a non-success HTTP status code."""

    status: int
    message: str
    details: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        detail = f" Details: {self.details}" if self.details else ""
        return f"HTTP {self.status}: {self.message}{detail}"


class RestconfNotFoundError(RestconfHTTPError):
    """Raised when a RESTCONF resource cannot be found (HTTP 404)."""
