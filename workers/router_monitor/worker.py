"""Background worker that monitors stored routers and updates status metadata."""
from __future__ import annotations

import asyncio
import sys
import time
from contextlib import suppress
from pathlib import Path

# Ensure project root is importable when executed as a script
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from config import settings
from utils.logger import configure_logging, get_logger

from workers.router_monitor.dependencies import ensure_dependencies, shutdown_dependencies
from workers.router_monitor.health_check import evaluate_router

configure_logging(settings.LOG_LEVEL)
_logger = get_logger(__name__)


async def _monitor_iteration(timeout: float, concurrency: int) -> None:
    deps = await ensure_dependencies()
    router_store = deps.router_store
    if router_store is None:
        raise RuntimeError("Router store not initialised")

    routers = await router_store.list_all_routers()
    if not routers:
        _logger.debug("No routers found to monitor")
        return

    semaphore = asyncio.Semaphore(max(concurrency, 1))

    async def _run_check(router_doc):
        async with semaphore:
            await evaluate_router(router_doc, router_store, timeout=timeout)

    await asyncio.gather(*(_run_check(router) for router in routers))


async def _monitor_loop() -> None:
    interval = max(settings.ROUTER_MONITOR_INTERVAL, 5)
    timeout = max(settings.ROUTER_MONITOR_TIMEOUT, 1.0)
    concurrency = max(settings.ROUTER_MONITOR_CONCURRENCY, 1)

    _logger.info(
        "Starting router monitor loop (interval=%ss, timeout=%ss, concurrency=%s)",
        interval,
        timeout,
        concurrency,
    )

    while True:
        iteration_start = time.monotonic()
        try:
            await _monitor_iteration(timeout, concurrency)
        except asyncio.CancelledError:  # pragma: no cover - cancellation path
            raise
        except Exception as exc:  # pragma: no cover - resiliency
            _logger.error("Router monitor iteration failed: %s", exc)

        elapsed = time.monotonic() - iteration_start
        sleep_for = max(interval - elapsed, 0)
        await asyncio.sleep(sleep_for)


async def main() -> None:
    try:
        await _monitor_loop()
    finally:
        await shutdown_dependencies()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
