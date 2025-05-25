# constants.py
# Legacy constants file - migrated to config.py
# This file is kept for backward compatibility

from aiogram import Dispatcher, Router
from config import Config

# Router and dispatcher instances
router = Router()
dp = Dispatcher()

# Legacy constants for backward compatibility
# These are now sourced from Config class
TOKEN = Config.BOT_TOKEN
CHANNEL_ID = Config.CHANNEL_ID
MONGO_URI = Config.MONGO_URI

# Developer info (now in Config)
DEVELOPER_USERNAME = Config.DEVELOPER_USERNAME
DEVELOPER_CHANNEL = Config.DEVELOPER_CHANNEL
