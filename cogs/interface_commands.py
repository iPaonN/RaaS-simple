"""
RESTCONF Interface Management Commands
"""
import discord
from discord import app_commands
from discord.ext import commands
from utils.restconf_client import RestConfClient
from utils.restconf_service import RestConfService
from utils.embeds import create_success_embed, create_error_embed, create_info_embed


class InterfaceCommands(commands.Cog):
    """Interface management commands via RESTCONF"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def _create_client(self, host: str, username: str, password: str) -> RestConfClient:
        """Create RESTCONF client instance"""
        return RestConfClient(host, username, password)
    
    @app_commands.command(name="get-interfaces", description="Get all interfaces from CSR1000v")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password"
    )
    async def get_interfaces(
        self,
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str
    ):
        """Get all interfaces from the router"""
        await interaction.response.defer()
        
        client = self._create_client(host, username, password)
        service = RestConfService(client)
        
        success, interfaces = await service.get_all_interfaces()
        
        if success:
            if not interfaces:
                embed = create_info_embed(
                    title="📡 Interfaces",
                    description="No interfaces found"
                )
            else:
                embed = create_success_embed(
                    title=f"📡 Interfaces on {host}",
                    description=f"Found {len(interfaces)} interface(s)"
                )
                
                for intf in interfaces[:10]:  # Limit to first 10
                    name = intf.get("name", "Unknown")
                    enabled = "✅" if intf.get("enabled", False) else "❌"
                    intf_type = intf.get("type", "N/A")
                    
                    embed.add_field(
                        name=f"{enabled} {name}",
                        value=f"Type: {intf_type}",
                        inline=True
                    )
                
                if len(interfaces) > 10:
                    embed.set_footer(text=f"Showing 10 of {len(interfaces)} interfaces")
            
            await interaction.followup.send(embed=embed)
        else:
            embed = create_error_embed(
                title="Connection Failed",
                description=f"Could not connect to {host}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="get-interface", description="Get specific interface details")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
        interface="Interface name (e.g., GigabitEthernet1)"
    )
    async def get_interface(
        self,
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
        interface: str
    ):
        """Get specific interface details"""
        await interaction.response.defer()
        
        client = self._create_client(host, username, password)
        service = RestConfService(client)
        
        success, intf_data = await service.get_interface(interface)
        
        if success and intf_data:
            name = intf_data.get("name", "Unknown")
            enabled = intf_data.get("enabled", False)
            status = "✅ Enabled" if enabled else "❌ Disabled"
            intf_type = intf_data.get("type", "N/A")
            description = intf_data.get("description", "No description")
            
            embed = create_info_embed(
                title=f"📡 Interface: {name}",
                description=f"**Status:** {status}\n**Type:** {intf_type}"
            )
            embed.add_field(name="Description", value=description, inline=False)
            
            # Add IP address if available
            ipv4 = intf_data.get("ietf-ip:ipv4", {})
            if ipv4:
                addresses = ipv4.get("address", [])
                if addresses:
                    ip_info = "\n".join([
                        f"{addr.get('ip', 'N/A')}/{addr.get('netmask', 'N/A')}"
                        for addr in addresses
                    ])
                    embed.add_field(name="IPv4 Addresses", value=ip_info, inline=False)
            
            await interaction.followup.send(embed=embed)
        else:
            embed = create_error_embed(
                title="Interface Not Found",
                description=f"Interface `{interface}` not found on {host}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="set-interface-description", description="Set interface description")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
        interface="Interface name (e.g., GigabitEthernet1)",
        description="New interface description"
    )
    async def set_interface_description(
        self,
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
        interface: str,
        description: str
    ):
        """Configure interface description"""
        await interaction.response.defer()
        
        client = self._create_client(host, username, password)
        service = RestConfService(client)
        
        success, result = await service.configure_interface_description(interface, description)
        
        if success:
            embed = create_success_embed(
                title="✅ Interface Configured",
                description=f"Successfully updated `{interface}` on {host}\n**Description:** {description}"
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = create_error_embed(
                title="Configuration Failed",
                description=f"Could not configure interface {interface}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="set-interface-state", description="Enable or disable an interface")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
        interface="Interface name (e.g., GigabitEthernet1)",
        enabled="Enable (True) or disable (False) the interface"
    )
    async def set_interface_state(
        self,
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
        interface: str,
        enabled: bool
    ):
        """Enable or disable an interface"""
        await interaction.response.defer()
        
        client = self._create_client(host, username, password)
        service = RestConfService(client)
        
        success, result = await service.set_interface_state(interface, enabled)
        
        if success:
            status = "enabled" if enabled else "disabled"
            embed = create_success_embed(
                title=f"✅ Interface {status.title()}",
                description=f"Successfully {status} `{interface}` on {host}"
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = create_error_embed(
                title="Configuration Failed",
                description=f"Could not modify interface {interface}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="set-interface-ip", description="Configure interface IP address")
    @app_commands.describe(
        host="Router IP address or hostname",
        username="RESTCONF username",
        password="RESTCONF password",
        interface="Interface name (e.g., GigabitEthernet1)",
        ip_address="IP address (e.g., 192.168.1.1)",
        netmask="Subnet mask (e.g., 255.255.255.0)"
    )
    async def set_interface_ip(
        self,
        interaction: discord.Interaction,
        host: str,
        username: str,
        password: str,
        interface: str,
        ip_address: str,
        netmask: str
    ):
        """Configure IP address on an interface"""
        await interaction.response.defer()
        
        client = self._create_client(host, username, password)
        service = RestConfService(client)
        
        success, result = await service.configure_interface_ip(interface, ip_address, netmask)
        
        if success:
            embed = create_success_embed(
                title="✅ IP Address Configured",
                description=f"Successfully configured `{interface}` on {host}\n**IP:** {ip_address}/{netmask}"
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = create_error_embed(
                title="Configuration Failed",
                description=f"Could not configure IP on {interface}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(InterfaceCommands(bot))
