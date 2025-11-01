"""Discord embeds for error reporting."""
from __future__ import annotations

import discord

from utils.embeds import create_error_embed

from .base import EmbedPresenter


class ErrorPresenter(EmbedPresenter):
    """Render RESTCONF error messages."""

    def render_error(self, message: str) -> discord.Embed:
        return create_error_embed(title="RESTCONF Error", description=message)
