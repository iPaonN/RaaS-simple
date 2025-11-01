"""
Discord Bot - Main Entry Point
"""
import discord
from discord.ext import commands
from config.settings import TOKEN, PREFIX, LOG_LEVEL, DEV_GUILD_ID
import logging
import os
from pathlib import Path

# Create logs directory if it doesn't exist
Path('logs').mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('discord')


class FemRouterBot(commands.Bot):
    """Custom Bot class with setup and initialization"""
    
    def __init__(self):
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None  # We'll use custom help command
        )
    
    async def setup_hook(self):
        """Load all cogs from the cogs directory"""
        logger.info("Loading cogs...")
        
        # Auto-load all cogs from the cogs directory
        cogs_dir = Path('./cogs')
        for file in cogs_dir.glob('*.py'):
            if file.name != '__init__.py':
                cog_name = f'cogs.{file.stem}'
                try:
                    await self.load_extension(cog_name)
                    logger.info(f'✓ Loaded {cog_name}')
                except Exception as e:
                    logger.error(f'✗ Failed to load {cog_name}: {e}')
        
        # Sync slash commands
        logger.info("Syncing slash commands...")
        try:
            if DEV_GUILD_ID and DEV_GUILD_ID > 0:
                # Try to sync to dev guild first (instant)
                guild = discord.Object(id=DEV_GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(f'✓ Synced {len(synced)} command(s) to dev guild ({DEV_GUILD_ID})')
            else:
                # Sync globally (takes ~1 hour to propagate)
                synced = await self.tree.sync()
                logger.info(f'✓ Synced {len(synced)} command(s) globally (may take up to 1 hour)')
        except discord.errors.Forbidden:
            logger.warning(f'⚠ Bot not in dev guild {DEV_GUILD_ID}, syncing globally instead...')
            try:
                synced = await self.tree.sync()
                logger.info(f'✓ Synced {len(synced)} command(s) globally (may take up to 1 hour)')
            except Exception as e:
                logger.error(f'✗ Failed to sync commands: {e}')
        except Exception as e:
            logger.error(f'✗ Failed to sync commands: {e}')
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guild(s)')
        logger.info('Bot is ready!')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="network devices 📡"
            )
        )
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        logger.error(f'Command error: {error}')


if __name__ == '__main__':
    bot = FemRouterBot()
    bot.run(TOKEN)
