"""Command group builders for RESTCONF slash commands."""

from .interface import InterfaceCommandGroup
from .device import DeviceCommandGroup
from .routing import RoutingCommandGroup

__all__ = [
    "InterfaceCommandGroup",
    "DeviceCommandGroup",
    "RoutingCommandGroup",
]
