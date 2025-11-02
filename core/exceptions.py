"""Custom exception hierarchy for the application."""

from __future__ import annotations


class FemrouterError(Exception):
    """Base error for domain-specific failures."""


class ConfigurationError(FemrouterError):
    """Raised when required configuration is missing or invalid."""


class InfrastructureError(FemrouterError):
    """Raised for infrastructure integration issues (DB, queues, etc.)."""
