"""
Utility Commands
"""
import discord
from discord import app_commands
from discord.ext import commands
import time
from datetime import datetime
from config.constants import BOT_VERSION
from utils.embeds import create_info_embed


class Utility(commands.Cog):
    """Utility and information commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        """Check bot latency"""
        latency = round(self.bot.latency * 1000)
        embed = create_info_embed(
            title="🏓 Pong!",
            description=f"Latency: **{latency}ms**"
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="serverinfo", description="Get information about the server")
    async def serverinfo(self, interaction: discord.Interaction):
        """Display server information"""
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"📊 {guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
        embed.add_field(name="Boosts", value=guild.premium_subscription_count or 0, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="userinfo", description="Get information about a user")
    @app_commands.describe(member="The member to get info about (leave empty for yourself)")
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member = None
    ):
        """Display user information"""
        member = member or interaction.user
        
        embed = discord.Embed(
            title=f"👤 {member.name}",
            color=member.color,
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(
            name="Account Created",
            value=member.created_at.strftime("%Y-%m-%d"),
            inline=True
        )
        embed.add_field(
            name="Joined Server",
            value=member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown",
            inline=True
        )
        embed.add_field(
            name="Top Role",
            value=member.top_role.mention,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="botinfo", description="Get information about the bot")
    async def botinfo(self, interaction: discord.Interaction):
        """Display bot information"""
        embed = discord.Embed(
            title=f"🤖 {self.bot.user.name}",
            description="A Discord bot built with discord.py",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        embed.add_field(name="Version", value=BOT_VERSION, inline=True)
        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=sum(g.member_count for g in self.bot.guilds), inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(
            name="Python",
            value=f"discord.py {discord.__version__}",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="help", description="Show all available commands")
    async def help(self, interaction: discord.Interaction):
        """Display help information"""
        embed = discord.Embed(
            title="📚 Bot Commands",
            description="Here are all available commands:",
            color=discord.Color.blue()
        )
        
        # Moderation commands
        embed.add_field(
            name="⚖️ Moderation",
            value=(
                "`/ban` - Ban a member\n"
                "`/kick` - Kick a member\n"
                "`/clear` - Clear messages"
            ),
            inline=False
        )
        
        # Fun commands
        embed.add_field(
            name="🎮 Fun",
            value=(
                "`/roll` - Roll a dice\n"
                "`/coinflip` - Flip a coin\n"
                "`/8ball` - Ask the magic 8-ball\n"
                "`/choose` - Choose from options"
            ),
            inline=False
        )
        
        # Utility commands
        embed.add_field(
            name="🔧 Utility",
            value=(
                "`/ping` - Check bot latency\n"
                "`/serverinfo` - Server information\n"
                "`/userinfo` - User information\n"
                "`/botinfo` - Bot information\n"
                "`/help` - Show this message"
            ),
            inline=False
        )
        
        # RESTCONF Interface commands
        embed.add_field(
            name="🌐 RESTCONF - Interfaces",
            value=(
                "`/get-interfaces` - List all interfaces\n"
                "`/get-interface` - Interface details\n"
                "`/set-interface-description` - Set description\n"
                "`/set-interface-state` - Enable/disable\n"
                "`/set-interface-ip` - Configure IP address"
            ),
            inline=False
        )
        
        # RESTCONF Device commands
        embed.add_field(
            name="🖥️ RESTCONF - Device",
            value=(
                "`/get-hostname` - Get hostname\n"
                "`/set-hostname` - Set hostname"
            ),
            inline=False
        )
        
        # RESTCONF Routing commands
        embed.add_field(
            name="🛣️ RESTCONF - Routing",
            value=(
                "`/get-routing-table` - Routing table\n"
                "`/get-static-routes` - Static routes"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Utility(bot))
