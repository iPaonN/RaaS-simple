"""Shared base helpers for RESTCONF presenters."""
from __future__ import annotations

from typing import Sequence


class EmbedPresenter:
    """Minimal base class with shared formatting helpers."""

    @staticmethod
    def _join_lines(lines: Sequence[str]) -> str:
        return "\n".join(line for line in lines if line)
