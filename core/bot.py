"""Discord bot wrapper with application-level wiring.

This module defines the high-level bot class that composes cogs,
configuration, and infrastructure services when the application starts.
"""

from __future__ import annotations

from typing import Callable, Sequence

from discord.ext import commands  # type: ignore[import]


class FemrouterBot(commands.Bot):
    """Discord bot subclass used across entrypoints."""

    def load_initial_cogs(self, cog_factories: Sequence[Callable[[commands.Bot], commands.Cog]]) -> None:
        """Register cogs created by the provided factory callables."""
        for factory in cog_factories:
            self.add_cog(factory(self))
