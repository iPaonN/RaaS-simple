"""Discord embeds for device-level views."""
from __future__ import annotations

import discord

from restconf.models import Banner, DeviceConfig, DomainName, Hostname, NameServerList
from utils.embeds import create_info_embed, create_success_embed

from .base import EmbedPresenter


class DevicePresenter(EmbedPresenter):
    """Render device metadata into embeds."""

    def render_hostname(self, host: str, hostname: Hostname) -> discord.Embed:
        return create_info_embed(
            title="🖥️ Device Hostname",
            description=f"**Hostname:** `{hostname.value}`\n**IP:** {host}",
        )

    def render_device_config(self, host: str, config: DeviceConfig) -> discord.Embed:
        config_title = "📄 Running Configuration" if config.config_type == "running" else "📄 Startup Configuration"
        embed = create_info_embed(
            title=f"{config_title} - {host}",
            description=f"**Size:** {config.size} bytes\n**Type:** {config.config_type.upper()}",
        )

        preview = config.preview
        if len(preview) > 1500:
            preview = preview[:1500] + "\n...(truncated)"

        embed.add_field(name="Configuration Preview", value=f"```json\n{preview}\n```", inline=False)
        embed.set_footer(text="⚠️ Configuration shown in JSON format. Full config may be longer.")
        return embed

    def render_banner(self, host: str, banner: Banner) -> discord.Embed:
        banner_title = "📢 MOTD Banner" if banner.banner_type == "motd" else "📢 Login Banner"

        if banner.is_configured:
            embed = create_info_embed(
                title=f"{banner_title} - {host}",
                description=f"**Type:** {banner.banner_type.upper()}",
            )
            display_message = banner.message if len(banner.message) <= 1000 else banner.message[:1000] + "\n...(truncated)"
            embed.add_field(name="Banner Message", value=f"```\n{display_message}\n```", inline=False)
        else:
            embed = create_info_embed(
                title=f"{banner_title} - {host}",
                description=f"**Type:** {banner.banner_type.upper()}\n\n*No banner configured*",
            )
        return embed

    def render_domain_name(self, host: str, domain: DomainName) -> discord.Embed:
        if domain.is_configured and domain.value != "No domain name configured":
            return create_info_embed(
                title=f"🌐 Domain Name - {host}",
                description=f"**Domain:** `{domain.value}`",
            )
        return create_info_embed(
            title=f"🌐 Domain Name - {host}",
            description="*No domain name configured*",
        )

    def render_name_servers(self, host: str, name_servers: NameServerList) -> discord.Embed:
        if not name_servers.is_configured:
            return create_info_embed(
                title=f"🌐 DNS Name Servers - {host}",
                description="No DNS name servers configured",
            )

        embed = create_success_embed(
            title=f"🌐 DNS Name Servers - {host}",
            description=f"**Total Servers:** {name_servers.count}",
        )
        for index, server in enumerate(name_servers.servers, start=1):
            embed.add_field(name=f"DNS Server {index}", value=f"`{server}`", inline=True)
        return embed
