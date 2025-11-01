"""
RESTCONF API Client
Handles all RESTCONF HTTP requests to Cisco devices
"""
import aiohttp
from typing import Optional, Tuple, Dict, Any
import logging

logger = logging.getLogger('restconf.client')


class RestConfClient:
    """RESTCONF API client for Cisco devices"""
    
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.base_url = f"https://{host}/restconf/data"
        self.auth = aiohttp.BasicAuth(username, password)
        self.headers = {
            "Accept": "application/yang-data+json",
            "Content-Type": "application/yang-data+json"
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Make a RESTCONF API request
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint path
            data: Optional request payload
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    auth=self.auth,
                    json=data,
                    ssl=False,  # Disable SSL verification for lab environments
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 201, 204]:
                        try:
                            result = await response.json()
                            return True, result
                        except:
                            return True, {}
                    else:
                        error_text = await response.text()
                        logger.error(f"Request failed: {response.status} - {error_text}")
                        return False, {
                            "error": error_text,
                            "status": response.status
                        }
        except aiohttp.ClientError as e:
            logger.error(f"Client error: {str(e)}")
            return False, {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return False, {"error": f"Unexpected error: {str(e)}"}
    
    async def get(self, endpoint: str) -> Tuple[bool, Dict[str, Any]]:
        """GET request"""
        return await self._request("GET", endpoint)
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """POST request"""
        return await self._request("POST", endpoint, data)
    
    async def put(self, endpoint: str, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """PUT request"""
        return await self._request("PUT", endpoint, data)
    
    async def patch(self, endpoint: str, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """PATCH request"""
        return await self._request("PATCH", endpoint, data)
    
    async def delete(self, endpoint: str) -> Tuple[bool, Dict[str, Any]]:
        """DELETE request"""
        return await self._request("DELETE", endpoint)
