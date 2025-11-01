"""RESTCONF presentation layer abstractions."""
from __future__ import annotations

from typing import Sequence

from restconf.models import (
    Banner,
    DeviceConfig,
    DomainName,
    Hostname,
    Interface,
    NameServerList,
    StaticRoute,
)

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


def render_device_config(host: str, config: DeviceConfig):
    return device_presenter.render_device_config(host, config)


def render_banner(host: str, banner: Banner):
    return device_presenter.render_banner(host, banner)


def render_domain_name(host: str, domain: DomainName):
    return device_presenter.render_domain_name(host, domain)


def render_name_servers(host: str, name_servers: NameServerList):
    return device_presenter.render_name_servers(host, name_servers)


def render_static_routes(host: str, routes: Sequence[StaticRoute]):
    return routing_presenter.render_static_routes(host, routes)


def render_restconf_error(message: str):
    return error_presenter.render_error(message)


__all__ = [
    "interface_presenter",
    "device_presenter",
    "routing_presenter",
    "error_presenter",
    "render_device_config",
    "render_banner",
    "render_domain_name",
    "render_name_servers",
    "render_interface_list",
    "render_interface",
    "render_hostname",
    "render_static_routes",
    "render_restconf_error",
]
