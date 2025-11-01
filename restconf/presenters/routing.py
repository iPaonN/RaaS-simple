"""Discord embeds for routing views."""
from __future__ import annotations

from typing import Sequence

import discord

from restconf.models import StaticRoute
from utils.embeds import create_info_embed, create_success_embed

from .base import EmbedPresenter


class RoutingPresenter(EmbedPresenter):
    """Render routing information into embeds."""

    def render_static_routes(self, host: str, routes: Sequence[StaticRoute]) -> discord.Embed:
        if not routes:
            return create_info_embed(
                title="🛣️ Static Routes",
                description="No static routes configured.",
            )

        embed = create_success_embed(
            title=f"🛣️ Static Routes on {host}",
            description=f"Found {len(routes)} static route(s).",
        )
        for route in routes[:5]:
            embed.add_field(
                name=route.prefix,
                value=f"Next Hop: {route.next_hop}",
                inline=False,
            )
        if len(routes) > 5:
            embed.set_footer(text=f"Showing 5 of {len(routes)} routes")
        return embed
