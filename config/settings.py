"""
Bot Settings and Environment Configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Token (required)
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError('DISCORD_TOKEN not found in environment variables!')

# Bot Configuration
PREFIX = os.getenv('PREFIX', '!')
DEV_GUILD_ID = int(os.getenv('DEV_GUILD_ID', 0)) if os.getenv('DEV_GUILD_ID') else None

# Database (optional)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/bot.db')
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DB = os.getenv('MONGODB_DB', 'femrouter')
MONGODB_ROUTER_COLLECTION = os.getenv('MONGODB_ROUTER_COLLECTION', 'routers')
MONGODB_TASK_COLLECTION = os.getenv('MONGODB_TASK_COLLECTION', 'tasks')

# RabbitMQ (optional)
RABBITMQ_URI = os.getenv('RABBITMQ_URI')
RABBITMQ_QUEUE = os.getenv('RABBITMQ_QUEUE', 'router_events')
RABBITMQ_TASK_QUEUE = os.getenv('RABBITMQ_TASK_QUEUE', 'router_tasks')

# Router monitor (optional)
ROUTER_MONITOR_INTERVAL = int(os.getenv('ROUTER_MONITOR_INTERVAL', '60'))
ROUTER_MONITOR_TIMEOUT = float(os.getenv('ROUTER_MONITOR_TIMEOUT', '5'))
ROUTER_MONITOR_CONCURRENCY = int(os.getenv('ROUTER_MONITOR_CONCURRENCY', '5'))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

# Bot Colors (for embeds)
COLOR_SUCCESS = 0x00ff00
COLOR_ERROR = 0xff0000
COLOR_INFO = 0x3498db
COLOR_WARNING = 0xffaa00
