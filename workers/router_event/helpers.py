"""Shared helper utilities for router event handling."""
from __future__ import annotations

from typing import Any

from infrastructure.mongodb.router_store import MongoRouterStore


async def load_router_credentials(
    router_store: MongoRouterStore,
    guild_id: int,
    router_ip: str,
) -> tuple[dict[str, Any], str, str]:
    """Retrieve stored router credentials for the given guild and IP."""

    router_doc = await router_store.get_router(guild_id, router_ip)
    if router_doc is None:
        raise RuntimeError(f"Router credentials not found for {router_ip}")
    username = router_doc.get("username")
    password = router_doc.get("password")
    if not username or not password:
        raise RuntimeError("Stored router credentials are incomplete")

    return router_doc, str(username), str(password)
