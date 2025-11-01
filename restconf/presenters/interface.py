"""Discord embeds for interface-focused views."""
from __future__ import annotations

from typing import Sequence

import discord

from restconf.models import Interface
from utils.embeds import create_info_embed, create_success_embed

from .base import EmbedPresenter


class InterfacePresenter(EmbedPresenter):
    """Render interface domain objects into embeds."""

    def render_list(self, host: str, interfaces: Sequence[Interface]) -> discord.Embed:
        if not interfaces:
            return create_info_embed(
                title="📡 Interfaces",
                description="No interfaces found on the device.",
            )

        embed = create_success_embed(
            title=f"📡 Interfaces on {host}",
            description=f"Found {len(interfaces)} interface(s).",
        )
        for interface in interfaces:
            details = [f"Type: {interface.type}"]
            if interface.ipv4_addresses:
                ips = ", ".join(f"{addr.ip}/{addr.netmask}" for addr in interface.ipv4_addresses)
                details.append(f"IPv4: {ips}")
            embed.add_field(
                name=f"{interface.status_emoji} {interface.name}",
                value=self._join_lines(details),
                inline=False,
            )
        return embed

    def render_detail(self, host: str, interface: Interface) -> discord.Embed:
        lines = [
            f"**Status:** {'Enabled' if interface.enabled else 'Disabled'}",
            f"**Type:** {interface.type}",
        ]
        if interface.description:
            lines.append(f"**Description:** {interface.description}")

        embed = create_info_embed(
            title=f"📡 Interface: {interface.name}",
            description=self._join_lines(lines),
        )

        if interface.ipv4_addresses:
            embed.add_field(
                name="IPv4 Addresses",
                value="\n".join(f"{addr.ip}/{addr.netmask}" for addr in interface.ipv4_addresses),
                inline=False,
            )
        return embed
