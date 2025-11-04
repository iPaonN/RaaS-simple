"""Health check task handler for the router event worker."""
from __future__ import annotations

from typing import Any, Optional

from restconf.client import RestconfClient
from restconf.service import RestconfService

from .dependencies import WorkerDependencies
from .helpers import load_router_credentials
from utils.logger import get_logger

_logger = get_logger(__name__)


async def process_health_task(payload: dict[str, Any], deps: WorkerDependencies) -> None:
    """Handle a router health audit task."""

    task_service = deps.task_service
    router_store = deps.router_store
    if task_service is None or router_store is None:
        raise RuntimeError("Task dependencies not initialised")

    task_id: Optional[str] = payload.get("task_id")
    router_ip: Optional[str] = payload.get("router_ip")
    guild_id: Optional[int] = payload.get("guild_id")

    if not task_id or not router_ip or guild_id is None:
        _logger.error("Received malformed health payload: %s", payload)
        return

    task = await task_service.get(task_id)
    if task is None:
        _logger.error("Task %s not found in repository", task_id)
        return

    task = await task_service.mark_running(task)
    metadata = task.metadata or {}
    task.metadata = metadata

    try:
        router_doc, username, password = await load_router_credentials(router_store, guild_id, router_ip)
        client = RestconfClient(router_ip, username, password, timeout=20.0)
        service = RestconfService(client)

        hostname_obj = await service.fetch_hostname()
        interfaces = await service.fetch_interfaces()
        try:
            routing_table = await service.fetch_routing_table()
            static_route_count = len(routing_table.static_routes)
        except Exception as exc:  # pragma: no cover - optional data path
            static_route_count = None
            _logger.warning("Failed to fetch routing table for %s: %s", router_ip, exc)

        enabled_interfaces = sum(1 for iface in interfaces if iface.enabled)
        summary_lines = [
            f"Hostname: {hostname_obj.value}",
            f"Interfaces: {len(interfaces)} total / {enabled_interfaces} up / {len(interfaces) - enabled_interfaces} down",
        ]
        if static_route_count is None:
            summary_lines.append("Static Routes: unavailable")
        else:
            summary_lines.append(f"Static Routes: {static_route_count}")

        metadata["router_label"] = (
            metadata.get("router_label")
            or hostname_obj.value
            or router_doc.get("name")
            or router_ip
        )
        metadata["health"] = {
            "hostname": hostname_obj.value,
            "interfaces_total": len(interfaces),
            "interfaces_up": enabled_interfaces,
            "interfaces_down": len(interfaces) - enabled_interfaces,
            "static_routes": static_route_count,
        }

        task = await task_service.mark_completed(task, "\n".join(summary_lines))
        _logger.info("Health task %s completed for %s", task.id, task.router_host)
    except Exception as exc:
        error_message = str(exc)
        metadata["error"] = error_message
        task = await task_service.mark_failed(task, error_message)
        _logger.error("Health task %s failed: %s", task_id, exc)
