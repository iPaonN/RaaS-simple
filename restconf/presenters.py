"""Presentation helpers for RESTCONF domain objects."""
from __future__ import annotations

from typing import Sequence

import discord

from restconf.models import Banner, DeviceConfig, DomainName, Hostname, Interface, NameServerList, RoutingTable, StaticRoute
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
    for interface in interfaces[:10]:
        value_lines = [f"Type: {interface.type}"]
        if interface.ipv4_addresses:
            ips = ", ".join(f"{addr.ip}/{addr.netmask}" for addr in interface.ipv4_addresses)
            value_lines.append(f"IPv4: {ips}")
        embed.add_field(
            name=f"{interface.status_emoji} {interface.name}",
            value="\n".join(value_lines),
            inline=False,
        )
    if len(interfaces) > 10:
        embed.set_footer(text=f"Showing 10 of {len(interfaces)} interfaces")
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


def render_device_config(host: str, config: DeviceConfig) -> discord.Embed:
    """Render device configuration in Discord embed."""
    config_title = "📄 Running Configuration" if config.config_type == "running" else "📄 Startup Configuration"
    
    embed = create_info_embed(
        title=f"{config_title} - {host}",
        description=f"**Size:** {config.size} bytes\n**Type:** {config.config_type.upper()}"
    )
    
    # Get preview (first 20 lines or 1500 chars, whichever is smaller)
    preview = config.preview
    if len(preview) > 1500:
        preview = preview[:1500] + "\n...(truncated)"
    
    embed.add_field(
        name="Configuration Preview",
        value=f"```json\n{preview}\n```",
        inline=False
    )
    
    embed.set_footer(text="⚠️ Configuration shown in JSON format. Full config may be longer.")
    
    return embed


def render_banner(host: str, banner: Banner) -> discord.Embed:
    """Render device banner in Discord embed."""
    banner_title = "📢 MOTD Banner" if banner.banner_type == "motd" else "📢 Login Banner"
    
    if banner.is_configured:
        embed = create_info_embed(
            title=f"{banner_title} - {host}",
            description=f"**Type:** {banner.banner_type.upper()}"
        )
        
        # Truncate message if too long
        display_message = banner.message
        if len(display_message) > 1000:
            display_message = display_message[:1000] + "\n...(truncated)"
        
        embed.add_field(
            name="Banner Message",
            value=f"```\n{display_message}\n```",
            inline=False
        )
    else:
        embed = create_info_embed(
            title=f"{banner_title} - {host}",
            description=f"**Type:** {banner.banner_type.upper()}\n\n*No banner configured*"
        )
    
    return embed


def render_domain_name(host: str, domain: DomainName) -> discord.Embed:
    """Render domain name in Discord embed."""
    
    if domain.is_configured and domain.value != "No domain name configured":
        embed = create_info_embed(
            title=f"🌐 Domain Name - {host}",
            description=f"**Domain:** `{domain.value}`"
        )
    else:
        embed = create_info_embed(
            title=f"🌐 Domain Name - {host}",
            description="*No domain name configured*"
        )
    
    return embed


def render_name_servers(host: str, name_servers: NameServerList) -> discord.Embed:
    """Render DNS name servers in Discord embed."""
    
    if name_servers.is_configured:
        embed = create_info_embed(
            title=f"🌐 DNS Name Servers - {host}",
            description=f"**Total Servers:** {name_servers.count}"
        )
        
        # Add each server as a field
        for idx, server in enumerate(name_servers.servers, 1):
            embed.add_field(
                name=f"DNS Server {idx}",
                value=f"`{server}`",
                inline=True
            )
    else:
        embed = create_info_embed(
            title=f"🌐 DNS Name Servers - {host}",
            description="No DNS name servers configured"
        )
    
    return embed
