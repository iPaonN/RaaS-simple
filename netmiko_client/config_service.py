"""Configuration backup service using Netmiko SSH."""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from netmiko import ConnectHandler

from utils.logger import get_logger

_logger = get_logger(__name__)


class ConfigService:
    """Service for backing up device configurations using SSH."""

    def __init__(self, host: str, username: str, password: str) -> None:
        self._host = host
        self._username = username
        self._password = password

    async def get_running_config(self) -> Path:
        """
        Use SSH (Netmiko) to retrieve running configuration from device.
        
        Returns:
            Path to the saved configuration file.
        """
        # Create netmiko_client/configs directory if it doesn't exist
        config_dir = Path("netmiko_client/configs")
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_filename = f"running_config_{self._host}_{timestamp}.txt"
        config_path = config_dir / config_filename
        
        # Run SSH command in thread pool
        loop = asyncio.get_event_loop()
        config_content = await loop.run_in_executor(None, self._get_config_via_ssh)
        
        # Save to file
        config_path.write_text(config_content)
        _logger.info("Configuration saved to %s", config_path)
        
        return config_path
    
    def _get_config_via_ssh(self) -> str:
        """Execute show running-config via SSH (blocking)."""
        _logger.info("Connecting to %s via Netmiko", self._host)
        
        # Device connection parameters
        device = {
            'device_type': 'cisco_ios',
            'host': self._host,
            'username': self._username,
            'password': self._password,
            'port': 22,
            'timeout': 30,
            'session_timeout': 60,
            'blocking_timeout': 30,
            'global_delay_factor': 2,
            # Support for legacy SSH algorithms
            'ssh_config_file': None,
            'allow_auto_change': True,
        }
        
        try:
            # Connect to device
            connection = ConnectHandler(**device)
            _logger.info("Connected to %s, executing show running-config", self._host)
            
            # Get running configuration
            config_output = connection.send_command(
                'show running-config',
                expect_string=r'#',
                read_timeout=60
            )
            
            # Disconnect
            connection.disconnect()
            
            if not config_output:
                raise RuntimeError("No configuration output received")
            
            _logger.info("Successfully retrieved configuration (%d bytes)", len(config_output))
            return config_output
            
        except Exception as e:
            _logger.error("SSH connection failed: %s", e)
            raise RuntimeError(f"Failed to get configuration via SSH: {str(e)}")
