"""
Embed Utilities
"""
import discord
from config.settings import COLOR_SUCCESS, COLOR_ERROR, COLOR_INFO, COLOR_WARNING


def create_success_embed(title: str, description: str = "") -> discord.Embed:
    """Create a success embed (green)"""
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=COLOR_SUCCESS
    )
    return embed


def create_error_embed(title: str, description: str = "") -> discord.Embed:
    """Create an error embed (red)"""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=COLOR_ERROR
    )
    return embed


def create_info_embed(title: str, description: str = "") -> discord.Embed:
    """Create an info embed (blue)"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=COLOR_INFO
    )
    return embed


def create_warning_embed(title: str, description: str = "") -> discord.Embed:
    """Create a warning embed (yellow/orange)"""
    embed = discord.Embed(
        title=f"⚠️ {title}",
        description=description,
        color=COLOR_WARNING
    )
    return embed
