"""Cog exposing router CRUD commands."""

from __future__ import annotations

from discord.ext import commands  # type: ignore[import]


class RouterManagement(commands.Cog):
    """Discord commands for managing router inventory."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="list_routers")
    async def list_routers(self, ctx: commands.Context) -> None:
        await ctx.send("Router management commands not yet implemented.")
