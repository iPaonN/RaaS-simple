"""Discord notification utilities for router event worker."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import aiohttp

from config import settings
from domain.entities.task import Task, TaskStatus
from utils.logger import get_logger

_logger = get_logger(__name__)


async def notify_discord(
    *,
    channel_id: Optional[int],
    user_id: Optional[int],
    task: Task,
    file_path: Optional[Path],
    note: Optional[str],
) -> None:
    """Send a Discord notification for task status updates."""

    token = settings.TOKEN
    if channel_id is None or not token:
        if not token:
            _logger.warning(
                "DISCORD_TOKEN not configured; skipping notification for task %s",
                task.id,
            )
        return

    mention = f"<@{user_id}> " if user_id else ""
    router_label = task.metadata.get("router_label") or task.router_host

    if task.status == TaskStatus.COMPLETED:
        base_message = f"✅ {mention}Backup task `{task.id}` for **{router_label}** completed."
        if note:
            base_message += f"\n📝 Note: {note}"
        content = base_message
    else:
        content = (
            f"❌ {mention}Backup task `{task.id}` for **{router_label}** failed.\n"
            f"Error: {task.result}"
        )

    headers = {"Authorization": f"Bot {token}"}
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"

    async with aiohttp.ClientSession() as session:
        if file_path and file_path.exists():
            with file_path.open("rb") as file_obj:
                form = aiohttp.FormData()
                form.add_field(
                    "payload_json",
                    json.dumps({"content": content}),
                    content_type="application/json",
                )
                form.add_field(
                    "files[0]",
                    file_obj,
                    filename=file_path.name,
                    content_type="text/plain",
                )
                async with session.post(url, headers=headers, data=form) as response:
                    if response.status >= 400:
                        body = await response.text()
                        _logger.error("Discord upload failed (%s): %s", response.status, body)
        else:
            async with session.post(url, headers=headers, json={"content": content}) as response:
                if response.status >= 400:
                    body = await response.text()
                    _logger.error("Discord notification failed (%s): %s", response.status, body)
