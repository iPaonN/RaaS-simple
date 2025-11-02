# Femrouter Discord Bot

A modular Discord automation platform for router management, built with `discord.py 2.x` and structured around clean architecture layers.

## Features

- ✅ Slash commands (app commands)
- 🔧 Modular cog system
- 🎨 Rich embeds
- ⚙️ Environment-based configuration
- 📝 Logging system
- 🔒 Permission checks
- 🧱 Layered architecture (core/domain/application/infrastructure)
- 👷 Dual entrypoints (`bot.py` for Discord, `worker.py` for background jobs)
- 🌐 RESTCONF API integration for Cisco CSR1000v
- 🎮 Fun commands & ⚖️ moderation tools
- 📊 Server/user info commands

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- A Discord bot token ([Get one here](https://discord.com/developers/applications))

### 2. Installation

```bash
# Clone or download this repository
cd femrouter

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux/Mac:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your bot token
# DISCORD_TOKEN=your_token_here
# DEV_GUILD_ID=your_test_server_id (optional but recommended)
```

### 4. Run the Bot

```bash
python bot.py
```

## Project Structure

```
femrouter/
├── bot.py                       # Discord bot entrypoint
├── worker.py                    # Background worker entrypoint
├── core/                        # Shared primitives (bot, db/queue abstractions)
├── domain/                      # Entities, repositories, services
├── application/                 # DTOs, use-cases, handlers
├── infrastructure/              # MongoDB & RabbitMQ adapters
├── cogs/                        # Discord command groups (incl. RESTCONF)
├── restconf/                    # Existing RESTCONF client/commands/presenters
├── config/                      # Settings, constants, logging config
├── utils/                       # Helpers (embeds, checks, decorators)
├── tests/                       # Unit & integration test scaffold
├── requirements.txt             # Python dependencies
├── docker-compose.yml           # Local stack (db/queue) scaffolding
└── .env.example                 # Example environment file
```

> ℹ️ The application follows a clean architecture: Discord-facing layers depend on domain interfaces, with MongoDB/RabbitMQ implementations living under `infrastructure/`.

## Available Commands

### Moderation (requires permissions)
- `/ban` - Ban a member from the server
- `/kick` - Kick a member from the server
- `/clear` - Clear messages from a channel

### Fun
- `/roll` - Roll a dice
- `/coinflip` - Flip a coin
- `/8ball` - Ask the magic 8-ball
- `/choose` - Choose from multiple options

### Utility
- `/ping` - Check bot latency
- `/serverinfo` - Get server information
- `/userinfo` - User information
- `/botinfo` - Get bot information
- `/help` - Show all commands

### RESTCONF - Interface Management
- `/get-interfaces` - Get all interfaces from router
- `/get-interface` - Get specific interface details
- `/set-interface-description` - Configure interface description
- `/set-interface-state` - Enable or disable an interface
- `/set-interface-ip` - Configure interface IP address

### RESTCONF - Device Configuration
- `/get-hostname` - Get router hostname
- `/set-hostname` - Set router hostname
- `/set-banner-motd` - Update MOTD banner
- `/set-domain-name` - Configure domain name
- `/get-name-servers` - View DNS servers
- `/save-config` - Save running configuration

### RESTCONF - Routing
- `/get-routing-table` - Get routing table information
- `/get-static-routes` - Get static routes

## Adding New Commands

### Create a new cog

Create a new file in `cogs/` directory:

```python
# cogs/example.py
import discord
from discord import app_commands
from discord.ext import commands

class Example(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="hello", description="Say hello")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello!")

async def setup(bot):
    await bot.add_cog(Example(bot))
```

The bot will automatically load all cogs in the `cogs/` directory on startup.

## Bot Setup on Discord

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section and create a bot
4. Copy the token and add it to your `.env` file
5. Enable these intents in the Bot settings:
   - Server Members Intent
   - Message Content Intent
6. Go to OAuth2 → URL Generator
7. Select scopes: `bot` and `applications.commands`
8. Select permissions you need (or Administrator for testing)
9. Use the generated URL to invite the bot to your server

## Development Tips

### Testing Commands
- Set `DEV_GUILD_ID` in `.env` to your test server ID
- Commands will sync instantly to that server (instead of 1 hour globally)
- Remove `DEV_GUILD_ID` when ready to deploy globally

### Logging
- Configure log formatting via `config/logging_config.py`
- Adjust `LOG_LEVEL` in `.env` (DEBUG, INFO, WARNING, ERROR)

### Error Handling
- Global error handlers are in `bot.py`
- Cog-specific error handlers can be added to each cog

## Deployment

### Option 1: Self-hosted (VPS)
```bash
# Install dependencies
pip install -r requirements.txt

# Run with screen or tmux
screen -S discord-bot
python bot.py
# Ctrl+A, D to detach
```

### Option 2: Docker (optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

### Option 3: Cloud Platforms
- Railway.app
- Render.com
- Fly.io
- Heroku

## Support

For discord.py help:
- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [discord.py Discord Server](https://discord.gg/dpy)

## License

MIT License - feel free to use this template for your own bots!
