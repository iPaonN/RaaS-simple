"""
RESTCONF Device Management Commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from utils.restconf_client import RestConfClient
from utils.restconf_service import RestConfService
from utils.embeds import create_success_embed, create_error_embed, create_info_embed


class DeviceCommands(commands.Cog):
    """Device management commands via RESTCONF"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def _create_client(self, host: str, username: str, password: str) -> RestConfClient:
        """Create RESTCONF client instance"""
        return RestConfClient(host, username, password)
    
    @app_commands.command(name="get-hostname", description="Get router hostname")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password"
    )
    async def get_hostname(
        self,
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str
    ):
        """Get router hostname"""
        await interaction.response.defer()
        
        client = self._create_client(host, username, password)
        service = RestConfService(client)
        
        success, hostname = await service.get_hostname()
        
        if success:
            embed = create_info_embed(
                title="🖥️ Router Hostname",
                description=f"**Hostname:** `{hostname}`\n**IP:** {host}"
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = create_error_embed(
                title="Request Failed",
                description=f"Could not get hostname from {host}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="set-hostname", description="Set router hostname")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
        hostname="New hostname"
    )
    async def set_hostname(
        self,
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
        hostname: str
    ):
        """Set router hostname"""
        await interaction.response.defer()
        
        client = self._create_client(host, username, password)
        service = RestConfService(client)
        
        success, result = await service.set_hostname(hostname)
        
        if success:
            embed = create_success_embed(
                title="✅ Hostname Updated",
                description=f"Successfully set hostname to `{hostname}` on {host}"
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = create_error_embed(
                title="Configuration Failed",
                description=f"Could not set hostname on {host}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(DeviceCommands(bot))
