"""
Moderation Commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import create_success_embed, create_error_embed


class Moderation(commands.Cog):
    """Moderation commands for managing the server"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(
        member="The member to ban",
        reason="Reason for the ban"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        """Ban a member from the server"""
        try:
            await member.ban(reason=f"{interaction.user}: {reason}")
            embed = create_success_embed(
                title="Member Banned",
                description=f"{member.mention} has been banned.\n**Reason:** {reason}"
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            embed = create_error_embed(
                title="Permission Error",
                description="I don't have permission to ban this member."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(
        member="The member to kick",
        reason="Reason for the kick"
    )
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        """Kick a member from the server"""
        try:
            await member.kick(reason=f"{interaction.user}: {reason}")
            embed = create_success_embed(
                title="Member Kicked",
                description=f"{member.mention} has been kicked.\n**Reason:** {reason}"
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            embed = create_error_embed(
                title="Permission Error",
                description="I don't have permission to kick this member."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="clear", description="Clear messages from a channel")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: int
    ):
        """Clear messages from a channel"""
        if amount < 1 or amount > 100:
            embed = create_error_embed(
                title="Invalid Amount",
                description="Please specify a number between 1 and 100."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            deleted = await interaction.channel.purge(limit=amount)
            embed = create_success_embed(
                title="Messages Cleared",
                description=f"Deleted {len(deleted)} message(s)."
            )
            await interaction.response.send_message(embed=embed, delete_after=5)
        except discord.Forbidden:
            embed = create_error_embed(
                title="Permission Error",
                description="I don't have permission to delete messages."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @ban.error
    @kick.error
    @clear.error
    async def moderation_error(self, interaction: discord.Interaction, error):
        """Error handler for moderation commands"""
        if isinstance(error, app_commands.MissingPermissions):
            embed = create_error_embed(
                title="Missing Permissions",
                description="You don't have permission to use this command."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Moderation(bot))
