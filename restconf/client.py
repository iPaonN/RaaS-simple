"""HTTP client for interacting with RESTCONF endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional, Callable
from pathlib import Path

import httpx

from restconf.errors import (
    RestconfConnectionError,
    RestconfHTTPError,
    RestconfNotFoundError,
)
from utils.logger import get_logger

_logger = get_logger(__name__)

ClientFactory = Callable[[], httpx.AsyncClient]


class RestconfClient:
    """Minimal RESTCONF client based on HTTPX."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        *,
        timeout: Optional[float] = 10.0,
        client_factory: Optional[ClientFactory] = None,
    ) -> None:
        self._host = host
        self._base_url = f"https://{host}/restconf/data"
        self._operations_url = f"https://{host}/restconf/operations"
        self._auth = (username, password)
        self._timeout = timeout
        self._client_factory = client_factory or self._default_client_factory

    def _default_client_factory(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            auth=self._auth,
            headers={
                "Accept": "application/yang-data+json",
                "Content-Type": "application/yang-data+json",
            },
            timeout=self._timeout,
            verify=False,  # Lab environments often use self-signed certificates
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute an HTTP request."""
        try:
            async with self._client_factory() as client:
                response = await client.request(method, endpoint, json=data)
        except httpx.TimeoutException as exc:  # pragma: no cover - network error path
            raise RestconfConnectionError("RESTCONF request timed out", host=self._host) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network error path
            raise RestconfConnectionError(str(exc), host=self._host) from exc

        if response.is_success:
            if response.status_code == httpx.codes.NO_CONTENT:
                return {}
            try:
                return response.json()
            except ValueError:  # pragma: no cover - malformed payload
                _logger.warning("Received non-JSON payload from %s", self._host)
                return {}

        payload: Optional[str]
        try:
            payload = response.text
        except Exception:  # pragma: no cover - httpx edge case
            payload = None

        if response.status_code == httpx.codes.NOT_FOUND:
            raise RestconfNotFoundError(status=response.status_code, message="Resource not found", details=payload)

        raise RestconfHTTPError(status=response.status_code, message=response.reason_phrase or "HTTP error", details=payload)

    async def get(self, endpoint: str) -> Dict[str, Any]:
        return await self._request("GET", endpoint)

    async def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PATCH", endpoint, data=data)

    async def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PUT", endpoint, data=data)

    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", endpoint, data=data)

    async def delete(self, endpoint: str) -> Dict[str, Any]:
        return await self._request("DELETE", endpoint)

    async def post_operation(self, operation: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a RESTCONF operation (RPC) via the operations endpoint."""
        try:
            async with httpx.AsyncClient(
                auth=self._auth,
                headers={
                    "Accept": "application/yang-data+json",
                    "Content-Type": "application/yang-data+json",
                },
                timeout=self._timeout,
                verify=False,
            ) as client:
                response = await client.post(
                    f"{self._operations_url}/{operation}",
                    json=data
                )
                
                if response.is_success:
                    if response.status_code == httpx.codes.NO_CONTENT:
                        return {}
                    try:
                        return response.json()
                    except ValueError:
                        return {}
                
                # Handle errors
                payload = response.text if response.text else None
                raise RestconfHTTPError(
                    status=response.status_code,
                    message=f"Operation failed: {response.reason_phrase}",
                    details=payload
                )
        except httpx.HTTPError as exc:
            raise RestconfConnectionError(str(exc), host=self._host) from exc
