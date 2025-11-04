"""Command group registration for asynchronous router tasks."""
from __future__ import annotations

from typing import Optional, Sequence

from discord import app_commands

from domain.services.task_service import TaskService
from infrastructure.messaging.rabbitmq import RabbitMQClient
from infrastructure.mongodb.router_store import MongoRouterStore
from restconf.command_groups.base import CommandGroup

from .task_backup import build_backup_command
from .task_health import build_health_check_command
from .task_status import build_task_status_command


class TaskCommandGroup(CommandGroup):
    """Factory for the task command group referencing modular builders."""

    def __init__(
        self,
        router_store: Optional[MongoRouterStore],
        task_service: Optional[TaskService],
        message_client: Optional[RabbitMQClient],
        task_queue_name: Optional[str],
    ) -> None:
        commands: Sequence[app_commands.Command] = [
            build_backup_command(router_store, task_service, message_client, task_queue_name),
            build_health_check_command(router_store, task_service, message_client, task_queue_name),
            build_task_status_command(task_service),
        ]
        super().__init__(commands)