"""
Permission Checks and Custom Decorators
"""
import discord
from discord import app_commands
from discord.ext import commands


def is_admin():
    """Check if user is admin"""
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


def is_mod():
    """Check if user is a moderator"""
    async def predicate(interaction: discord.Interaction) -> bool:
        return (
            interaction.user.guild_permissions.kick_members or
            interaction.user.guild_permissions.ban_members or
            interaction.user.guild_permissions.manage_messages
        )
    return app_commands.check(predicate)


def is_owner():
    """Check if user is the bot owner"""
    async def predicate(interaction: discord.Interaction) -> bool:
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(predicate)
