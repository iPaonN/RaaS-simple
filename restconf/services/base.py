"""Base classes shared by RESTCONF services."""
from __future__ import annotations

from restconf.client import RestconfClient


class RestconfDomainService:
    """Base class for service objects that operate on a RESTCONF client."""

    def __init__(self, client: RestconfClient) -> None:
        self._client = client

    @property
    def client(self) -> RestconfClient:
        """Return the underlying RESTCONF client."""
        return self._client
