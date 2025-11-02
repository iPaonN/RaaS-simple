"""Pytest fixtures for the project."""

from __future__ import annotations

import pytest  # type: ignore[import]


@pytest.fixture
async def event_loop():  # type: ignore[override]
    """Provide an event loop for async tests."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
