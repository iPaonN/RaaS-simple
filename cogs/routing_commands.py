"""
RESTCONF Routing Commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from utils.restconf_client import RestConfClient
from utils.restconf_service import RestConfService
from utils.embeds import create_success_embed, create_error_embed, create_info_embed


class RoutingCommands(commands.Cog):
    """Routing management commands via RESTCONF"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def _create_client(self, host: str, username: str, password: str) -> RestConfClient:
        """Create RESTCONF client instance"""
        return RestConfClient(host, username, password)
    
    @app_commands.command(name="get-routing-table", description="Get routing table information")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password"
    )
    async def get_routing_table(
        self,
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str
    ):
        """Get routing table information"""
        await interaction.response.defer()
        
        client = self._create_client(host, username, password)
        service = RestConfService(client)
        
        success, routing_data = await service.get_routing_table()
        
        if success:
            embed = create_info_embed(
                title=f"🛣️ Routing Table - {host}",
                description="Routing information retrieved successfully"
            )
            
            embed.add_field(
                name="Status",
                value="✅ Retrieved successfully",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        else:
            embed = create_error_embed(
                title="Request Failed",
                description=f"Could not get routing table from {host}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="get-static-routes", description="Get static routes")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password"
    )
    async def get_static_routes(
        self,
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str
    ):
        """Get static routes"""
        await interaction.response.defer()
        
        client = self._create_client(host, username, password)
        service = RestConfService(client)
        
        success, routes = await service.get_static_routes()
        
        if success:
            if not routes:
                embed = create_info_embed(
                    title="🛣️ Static Routes",
                    description="No static routes configured"
                )
            else:
                embed = create_success_embed(
                    title=f"🛣️ Static Routes - {host}",
                    description=f"Found {len(routes)} static route(s)"
                )
                
                for route in routes[:5]:  # Limit to first 5
                    if isinstance(route, dict):
                        prefix = route.get("prefix", "Unknown")
                        next_hop = route.get("next-hop", "Unknown")
                        
                        embed.add_field(
                            name=f"Route: {prefix}",
                            value=f"Next Hop: {next_hop}",
                            inline=False
                        )
                
                if len(routes) > 5:
                    embed.set_footer(text=f"Showing 5 of {len(routes)} routes")
            
            await interaction.followup.send(embed=embed)
        else:
            embed = create_error_embed(
                title="Request Failed",
                description=f"Could not get static routes from {host}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(RoutingCommands(bot))
