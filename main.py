"""
Main bot file with modular imports
"""
import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Config
from constants import dp, router
from db import mongo_client
from utils.logger import logger, log_system_event
from utils.backup import scheduled_backup_task

# Import all handlers
from handlers import (
    start,
    post_creation,
    post_settings,
    buttons,
    media,
    text_input,
    preview_publish,
    chat,
    stats,
    connect,
    channel_selection,
    edit_post,
    admin  # Import admin handlers
)

async def main() -> None:
    # Validate configuration
    Config.validate()
    log_system_event("Configuration validated successfully")
    
    logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))

    dp.include_routers(router)

    bot = Bot(Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Test database connection
    await mongo_client.admin.command("ismaster")
    log_system_event("Database connection established")
    
    # Start scheduled backup task if enabled
    if Config.ENABLE_BACKUP:
        asyncio.create_task(scheduled_backup_task())
        log_system_event("Scheduled backup task started")
    
    log_system_event("PostBot started successfully")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
