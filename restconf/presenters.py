"""Presentation helpers for RESTCONF domain objects."""
from __future__ import annotations

from typing import Sequence

import discord

from restconf.models import Hostname, Interface, RoutingTable, StaticRoute
from utils.embeds import (
    create_error_embed,
    create_info_embed,
    create_success_embed,
)


def render_interface_list(host: str, interfaces: Sequence[Interface]) -> discord.Embed:
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
        value_lines = [f"Type: {interface.type}"]
        if interface.ipv4_addresses:
            ips = ", ".join(f"{addr.ip}/{addr.netmask}" for addr in interface.ipv4_addresses)
            value_lines.append(f"IPv4: {ips}")
        embed.add_field(
            name=f"{interface.status_emoji} {interface.name}",
            value="\n".join(value_lines),
            inline=False,
        )
    return embed


def render_interface(host: str, interface: Interface) -> discord.Embed:
    description_lines = [
        f"**Status:** {'Enabled' if interface.enabled else 'Disabled'}",
        f"**Type:** {interface.type}",
    ]
    if interface.description:
        description_lines.append(f"**Description:** {interface.description}")

    embed = create_info_embed(
        title=f"📡 Interface: {interface.name}",
        description="\n".join(description_lines),
    )

    if interface.ipv4_addresses:
        embed.add_field(
            name="IPv4 Addresses",
            value="\n".join(f"{addr.ip}/{addr.netmask}" for addr in interface.ipv4_addresses),
            inline=False,
        )
    return embed


def render_hostname(host: str, hostname: Hostname) -> discord.Embed:
    return create_info_embed(
        title="🖥️ Device Hostname",
        description=f"**Hostname:** `{hostname.value}`\n**IP:** {host}",
    )


def render_static_routes(host: str, routes: Sequence[StaticRoute]) -> discord.Embed:
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


def render_routing_table(host: str, table: RoutingTable) -> discord.Embed:
    embed = create_info_embed(
        title=f"🛣️ Routing Table - {host}",
        description="Routing information retrieved successfully.",
    )
    embed.add_field(
        name="Static Routes",
        value=str(len(table.static_routes)),
        inline=False,
    )
    return embed


def render_restconf_error(message: str) -> discord.Embed:
    return create_error_embed(title="RESTCONF Error", description=message)
