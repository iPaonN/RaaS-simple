"""Entry point for the router event worker."""
from __future__ import annotations

import asyncio
import sys
from contextlib import suppress
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from workers.router_event.worker import main as run_worker


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(run_worker())