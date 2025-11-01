"""RESTCONF presentation layer abstractions."""
from __future__ import annotations

from typing import Sequence

from restconf.models import Hostname, Interface, StaticRoute

from .device import DevicePresenter
from .errors import ErrorPresenter
from .interface import InterfacePresenter
from .routing import RoutingPresenter

interface_presenter = InterfacePresenter()
device_presenter = DevicePresenter()
routing_presenter = RoutingPresenter()
error_presenter = ErrorPresenter()


def render_interface_list(host: str, interfaces: Sequence[Interface]):
    return interface_presenter.render_list(host, interfaces)


def render_interface(host: str, interface: Interface):
    return interface_presenter.render_detail(host, interface)


def render_hostname(host: str, hostname: Hostname):
    return device_presenter.render_hostname(host, hostname)


def render_static_routes(host: str, routes: Sequence[StaticRoute]):
    return routing_presenter.render_static_routes(host, routes)


def render_restconf_error(message: str):
    return error_presenter.render_error(message)


__all__ = [
    "interface_presenter",
    "device_presenter",
    "routing_presenter",
    "error_presenter",
    "render_interface_list",
    "render_interface",
    "render_hostname",
    "render_static_routes",
    "render_restconf_error",
]
