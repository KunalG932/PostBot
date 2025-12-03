"""
Main bot file with modular imports and health check server
"""
import asyncio
import logging
from aiohttp import web

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

# Health check server for Koyeb
async def health_check(request):
    """Health check endpoint for Koyeb"""
    return web.Response(text="OK", status=200)

async def start_health_server():
    """Start health check HTTP server on port 8000"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    log_system_event("Health check server started on port 8000")

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
    
    # Start health check server for Koyeb
    asyncio.create_task(start_health_server())
    
    # Start scheduled backup task if enabled
    if Config.ENABLE_BACKUP:
        asyncio.create_task(scheduled_backup_task())
        log_system_event("Scheduled backup task started")
    
    log_system_event("PostBot started successfully")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
