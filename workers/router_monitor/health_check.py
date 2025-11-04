"""Router status evaluation utilities for the monitor worker."""
from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

from restconf.client import RestconfClient
from restconf.errors import RestconfConnectionError, RestconfHTTPError
from restconf.service import RestconfService

from infrastructure.mongodb.router_store import MongoRouterStore
from utils.logger import get_logger

_logger = get_logger(__name__)


class RouterDocument(TypedDict, total=False):
    guild_id: int
    ip: str
    username: str
    password: str
    status: str


async def evaluate_router(
    router: RouterDocument,
    store: MongoRouterStore,
    *,
    timeout: float,
) -> None:
    """Check router reachability and update stored status."""

    guild_id = router.get("guild_id")
    ip = router.get("ip")
    username = router.get("username")
    password = router.get("password")

    if guild_id is None or not ip:
        _logger.debug("Skipping router without guild/ip: %s", router)
        return

    if not username or not password:
        await store.set_status(
            guild_id,
            ip,
            "invalid",
            failure_reason="Credentials missing",
        )
        return

    client = RestconfClient(ip, username, password, timeout=timeout)
    service = RestconfService(client)
    now = datetime.utcnow()

    try:
        await service.fetch_hostname()
    except RestconfHTTPError as exc:
        await store.set_status(
            guild_id,
            ip,
            "auth_failed",
            failure_reason=str(exc),
        )
        _logger.warning("Authentication failed for router %s (guild %s): %s", ip, guild_id, exc)
    except RestconfConnectionError as exc:
        await store.set_status(
            guild_id,
            ip,
            "offline",
            failure_reason=str(exc),
        )
        _logger.warning("Connection failed for router %s (guild %s): %s", ip, guild_id, exc)
    except Exception as exc:  # pragma: no cover - defensive path
        await store.set_status(
            guild_id,
            ip,
            "error",
            failure_reason=str(exc),
        )
        _logger.error("Unexpected error probing router %s (guild %s): %s", ip, guild_id, exc)
    else:
        await store.set_status(
            guild_id,
            ip,
            "online",
            last_seen=now,
            failure_reason=None,
        )
        # Only log when recovering from non-online status to reduce noise.
        if router.get("status") != "online":
            _logger.info("Router %s (guild %s) is online", ip, guild_id)
