"""
Main bot file with modular imports
"""
import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from constants import TOKEN, CHANNEL_ID, dp, router
from db import mongo_client

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
    clone_quote,
    stats,
    connect,
    channel_selection,
    edit_post
)

async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    dp.include_routers(router)

    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await mongo_client.admin.command("ismaster")

    await dp.start_polling(bot)
    await bot.send_message(chat_id=CHANNEL_ID, text="✅ Bot is now alive and modular!")


if __name__ == "__main__":
    asyncio.run(main())
