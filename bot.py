"""
Discord Bot - Main Entry Point
"""
import discord
from discord.ext import commands
import logging
import asyncio
from pathlib import Path

from config.settings import TOKEN, PREFIX, DEV_GUILD_ID

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('bot')


class DiscordBot(commands.Bot):
    """Custom Bot class with setup and initialization"""
    
    def __init__(self):
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None  # We'll create a custom help command
        )
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        # Load all cogs
        cogs_dir = Path('cogs')
        for cog_file in cogs_dir.glob('*.py'):
            if cog_file.stem != '__init__':
                try:
                    await self.load_extension(f'cogs.{cog_file.stem}')
                    logger.info(f'✅ Loaded cog: {cog_file.stem}')
                except Exception as e:
                    logger.error(f'❌ Failed to load cog {cog_file.stem}: {e}')
        
        # Sync commands
        if DEV_GUILD_ID:
            # Sync to dev guild for instant testing
            guild = discord.Object(id=DEV_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f'✅ Synced commands to dev guild: {DEV_GUILD_ID}')
        else:
            # Sync globally (takes ~1 hour to propagate)
            await self.tree.sync()
            logger.info('✅ Synced commands globally')
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'🤖 Logged in as {self.user} (ID: {self.user.id})')
        logger.info(f'📊 Connected to {len(self.guilds)} guilds')
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/help"
            )
        )
    
    async def on_command_error(self, ctx, error):
        """Global error handler for prefix commands"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send('❌ You don\'t have permission to use this command.')
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'❌ Missing required argument: `{error.param.name}`')
        else:
            logger.error(f'Error in command {ctx.command}: {error}')


async def main():
    """Main function to run the bot"""
    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)
    
    # Create and run bot
    bot = DiscordBot()
    
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        logger.info('🛑 Shutting down bot...')
        await bot.close()


if __name__ == '__main__':
    asyncio.run(main())
