"""Discord embeds for device-level views."""
from __future__ import annotations

import discord

from restconf.models import Hostname
from utils.embeds import create_info_embed

from .base import EmbedPresenter


class DevicePresenter(EmbedPresenter):
    """Render device metadata into embeds."""

    def render_hostname(self, host: str, hostname: Hostname) -> discord.Embed:
        return create_info_embed(
            title="🖥️ Device Hostname",
            description=f"**Hostname:** `{hostname.value}`\n**IP:** {host}",
        )
