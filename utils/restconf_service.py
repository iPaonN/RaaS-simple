"""
RESTCONF Service Layer
Business logic for RESTCONF operations
"""
from typing import List, Dict, Any, Optional, Tuple
from utils.restconf_client import RestConfClient


class RestConfService:
    """Service layer for RESTCONF operations"""
    
    def __init__(self, client: RestConfClient):
        self.client = client
    
    async def get_all_interfaces(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Get all interfaces from the device
        
        Returns:
            Tuple of (success: bool, interfaces: list)
        """
        success, result = await self.client.get("ietf-interfaces:interfaces")
        
        if success:
            interfaces = result.get("ietf-interfaces:interfaces", {}).get("interface", [])
            return True, interfaces
        return False, []
    
    async def get_interface(self, interface_name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get specific interface details
        
        Args:
            interface_name: Name of the interface (e.g., GigabitEthernet1)
            
        Returns:
            Tuple of (success: bool, interface_data: dict)
        """
        endpoint = f"ietf-interfaces:interfaces/interface={interface_name}"
        success, result = await self.client.get(endpoint)
        
        if success:
            interface_data = result.get("ietf-interfaces:interface", {})
            return True, interface_data
        return False, result
    
    async def configure_interface_description(
        self,
        interface_name: str,
        description: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Configure interface description
        
        Args:
            interface_name: Name of the interface
            description: New description
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        endpoint = f"ietf-interfaces:interfaces/interface={interface_name}"
        data = {
            "ietf-interfaces:interface": {
                "name": interface_name,
                "description": description,
                "type": "iana-if-type:ethernetCsmacd"
            }
        }
        
        return await self.client.patch(endpoint, data)
    
    async def set_interface_state(
        self,
        interface_name: str,
        enabled: bool
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Enable or disable an interface
        
        Args:
            interface_name: Name of the interface
            enabled: True to enable, False to disable
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        endpoint = f"ietf-interfaces:interfaces/interface={interface_name}"
        data = {
            "ietf-interfaces:interface": {
                "name": interface_name,
                "enabled": enabled,
                "type": "iana-if-type:ethernetCsmacd"
            }
        }
        
        return await self.client.patch(endpoint, data)
    
    async def configure_interface_ip(
        self,
        interface_name: str,
        ip_address: str,
        netmask: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Configure IP address on an interface
        
        Args:
            interface_name: Name of the interface
            ip_address: IP address
            netmask: Subnet mask (e.g., 255.255.255.0)
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        endpoint = f"ietf-interfaces:interfaces/interface={interface_name}"
        data = {
            "ietf-interfaces:interface": {
                "name": interface_name,
                "type": "iana-if-type:ethernetCsmacd",
                "ietf-ip:ipv4": {
                    "address": [
                        {
                            "ip": ip_address,
                            "netmask": netmask
                        }
                    ]
                }
            }
        }
        
        return await self.client.patch(endpoint, data)
    
    async def get_hostname(self) -> Tuple[bool, str]:
        """
        Get device hostname
        
        Returns:
            Tuple of (success: bool, hostname: str)
        """
        success, result = await self.client.get("Cisco-IOS-XE-native:native/hostname")
        
        if success:
            hostname = result.get("Cisco-IOS-XE-native:hostname", "Unknown")
            return True, hostname
        return False, ""
    
    async def set_hostname(self, hostname: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Set device hostname
        
        Args:
            hostname: New hostname
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        endpoint = "Cisco-IOS-XE-native:native/hostname"
        data = {
            "Cisco-IOS-XE-native:hostname": hostname
        }
        
        return await self.client.patch(endpoint, data)
    
    async def get_routing_table(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Get routing table information
        
        Returns:
            Tuple of (success: bool, routing_data: dict)
        """
        success, result = await self.client.get("ietf-routing:routing")
        
        if success:
            routing_data = result.get("ietf-routing:routing", {})
            return True, routing_data
        return False, result
    
    async def get_static_routes(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Get static routes
        
        Returns:
            Tuple of (success: bool, routes: list)
        """
        endpoint = "Cisco-IOS-XE-native:native/ip/route"
        success, result = await self.client.get(endpoint)
        
        if success:
            routes = result.get("Cisco-IOS-XE-native:route", {})
            return True, routes if isinstance(routes, list) else [routes]
        return False, []
