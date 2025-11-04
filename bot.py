"""Discord bot entry point."""
from __future__ import annotations

from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore[import]

from config.settings import (
    DEV_GUILD_ID,
    LOG_LEVEL,
    MONGODB_DB,
    MONGODB_ROUTER_COLLECTION,
    MONGODB_TASK_COLLECTION,
    MONGODB_URI,
    PREFIX,
    TOKEN,
)
from infrastructure.mongodb.router_store import MongoRouterStore
from infrastructure.mongodb.repositories import MongoTaskRepository
from domain.services.task_service import TaskService
from utils.embeds import create_error_embed
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
        self.mongo_client: AsyncIOMotorClient | None = None
        self.router_store: MongoRouterStore | None = None
        self.task_service: TaskService | None = None
    
    async def setup_hook(self) -> None:
        """Load all cogs from the cogs directory"""
        logger.info("Loading cogs...")

        self._initialise_mongo()
        
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

    def _initialise_mongo(self) -> None:
        """Initialise MongoDB client if configuration is provided."""

        if not MONGODB_URI:
            logger.info("MONGODB_URI not set; Mongo-backed features disabled")
            self.router_store = None
            self.task_service = None
            return

        try:
            self.mongo_client = AsyncIOMotorClient(MONGODB_URI)
            database = self.mongo_client[MONGODB_DB]
            collection = database[MONGODB_ROUTER_COLLECTION]
            self.router_store = MongoRouterStore(collection)
            task_collection = database[MONGODB_TASK_COLLECTION]
            task_repository = MongoTaskRepository(task_collection)
            self.task_service = TaskService(task_repository)
            logger.info(
                "MongoDB initialised (db=%s, routers=%s, tasks=%s)",
                MONGODB_DB,
                MONGODB_ROUTER_COLLECTION,
                MONGODB_TASK_COLLECTION,
            )
        except Exception as exc:  # pragma: no cover - connection failure path
            logger.error("Failed to initialise MongoDB client: %s", exc)
            self.mongo_client = None
            self.router_store = None
            self.task_service = None

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
        """Handle prefix command errors by notifying the user."""

        if isinstance(error, commands.CommandNotFound):
            return

        root_error = error
        if isinstance(error, commands.CommandInvokeError) and error.original:
            root_error = error.original

        logger.exception("Command error", exc_info=root_error)

        await self._send_command_error(ctx=ctx, message=self._format_error_message(root_error))

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Handle slash command errors and send feedback to the invoker."""

        root_error: Exception = error
        if isinstance(error, app_commands.CommandInvokeError) and error.original:
            root_error = error.original

        logger.exception("App command error", exc_info=root_error)

        await self._send_command_error(interaction=interaction, message=self._format_error_message(root_error))

    async def _send_command_error(
        self,
        *,
        ctx: commands.Context | None = None,
        interaction: discord.Interaction | None = None,
        message: str,
    ) -> None:
        """Deliver an error embed back to the issuer, handling both command styles."""

        embed = create_error_embed("Command failed", message)

        try:
            if interaction is not None:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            elif ctx is not None:
                await ctx.reply(embed=embed, mention_author=False)
        except Exception as exc:  # pragma: no cover - notification failure
            logger.exception("Failed to notify user about command error", exc_info=exc)

    @staticmethod
    def _format_error_message(error: Exception) -> str:
        """Return a concise, user-friendly error description."""

        message = str(error).strip()
        if not message:
            message = error.__class__.__name__
        if len(message) > 500:
            message = f"{message[:497]}…"
        return message

    async def close(self) -> None:
        if self.mongo_client:
            self.mongo_client.close()
        await super().close()


if __name__ == '__main__':
    bot = FemRouterBot()
    bot.run(TOKEN)
