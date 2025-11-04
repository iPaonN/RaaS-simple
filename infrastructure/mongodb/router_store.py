"""MongoDB-backed persistence helpers for router connection profiles."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorCollection  # type: ignore[import]


class MongoRouterStore:
    """Persists router connection metadata for guild-specific usage."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def upsert_router(self, router: dict[str, Any]) -> dict[str, Any]:
        """Insert or update a router profile and return the stored document."""

        now = datetime.utcnow()
        router = {**router, "updated_at": now}
        router.setdefault("last_checked", now)
        router.setdefault("metadata", {})

        filter_doc = {"guild_id": router["guild_id"], "ip": router["ip"]}
        update_doc = {
            "$set": router,
            "$setOnInsert": {"created_at": now},
        }
        await self._collection.update_one(filter_doc, update_doc, upsert=True)
        stored = await self._collection.find_one(filter_doc)
        return stored or router

    async def list_routers(self, guild_id: int) -> list[dict[str, Any]]:
        cursor = self._collection.find({"guild_id": guild_id}).sort("name", 1)
        return [doc async for doc in cursor]

    async def get_router(self, guild_id: int, ip: str) -> Optional[dict[str, Any]]:
        return await self._collection.find_one({"guild_id": guild_id, "ip": ip})

    async def set_status(self, guild_id: int, ip: str, status: str) -> None:
        await self._collection.update_one(
            {"guild_id": guild_id, "ip": ip},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    async def delete_router(self, guild_id: int, ip: str) -> int:
        """Remove a stored router profile. Returns number of deleted documents."""

        result = await self._collection.delete_one({"guild_id": guild_id, "ip": ip})
        return result.deleted_count