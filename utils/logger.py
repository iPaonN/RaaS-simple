"""Centralised logging utilities with structured output."""
from __future__ import annotations

import json
import logging
from logging import Logger
from pathlib import Path
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - trivial
        payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = record.stack_info
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", *, log_dir: str = "logs") -> None:
    """Configure root logging with JSON output and file/stream handlers."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.handlers.clear()
    level_name = level.upper()
    level_value = logging.getLevelName(level_name)
    if isinstance(level_value, str):  # pragma: no cover - defensive
        level_value = logging.INFO
    root.setLevel(level_value)

    formatter = JsonFormatter()

    file_handler = logging.FileHandler(Path(log_dir) / "bot.log")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level_value)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level_value)

    root.addHandler(file_handler)
    root.addHandler(stream_handler)


def get_logger(name: str) -> Logger:
    """Return module-specific logger."""
    return logging.getLogger(name)
