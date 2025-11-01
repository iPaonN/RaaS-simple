"""Discord bot entry point."""
from __future__ import annotations

from pathlib import Path

import discord
from discord.ext import commands

from config.settings import DEV_GUILD_ID, LOG_LEVEL, PREFIX, TOKEN
from utils.logger import configure_logging, get_logger

# Configure structured logging before the bot starts to log anything.
configure_logging(LOG_LEVEL)

logger = get_logger(__name__)


class FemRouterBot(commands.Bot):
    """Custom Bot class with setup and initialization"""
    
    def __init__(self) -> None:
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None  # We'll use custom help command
        )
    
    async def setup_hook(self) -> None:
        """Load all cogs from the cogs directory"""
        logger.info("Loading cogs...")
        
        # Auto-load all cogs from the cogs directory
        cogs_dir = Path("./cogs")
        for file in cogs_dir.glob("*.py"):
            if file.name != "__init__.py":
                cog_name = f"cogs.{file.stem}"
                try:
                    await self.load_extension(cog_name)
                    logger.info("Loaded %s", cog_name)
                except Exception as exc:
                    logger.error("Failed to load %s: %s", cog_name, exc)
        
        # Sync slash commands
        logger.info("Syncing slash commands...")
        try:
            if DEV_GUILD_ID and DEV_GUILD_ID > 0:
                # Try to sync to dev guild first (instant)
                guild = discord.Object(id=DEV_GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(
                    "Synced %s command(s) to dev guild %s",
                    len(synced),
                    DEV_GUILD_ID,
                )
            else:
                # Sync globally (takes ~1 hour to propagate)
                synced = await self.tree.sync()
                logger.info(
                    "Synced %s command(s) globally (may take up to 1 hour)",
                    len(synced),
                )
        except discord.errors.Forbidden:
            logger.warning(
                "Bot not in dev guild %s, syncing globally instead...",
                DEV_GUILD_ID,
            )
            try:
                synced = await self.tree.sync()
                logger.info(
                    "Synced %s command(s) globally (may take up to 1 hour)",
                    len(synced),
                )
            except Exception as exc:
                logger.error("Failed to sync commands: %s", exc)
        except Exception as exc:
            logger.error("Failed to sync commands: %s", exc)

    async def on_ready(self) -> None:
        """Called when bot is ready"""
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        logger.info("Connected to %s guild(s)", len(self.guilds))
        logger.info("Bot is ready!")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="network devices 📡"
            )
        )
    
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        logger.error("Command error: %s", error)


if __name__ == '__main__':
    bot = FemRouterBot()
    bot.run(TOKEN)
