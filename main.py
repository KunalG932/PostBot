import asyncio
import logging
from os import getenv

from handlers.start import start_router

from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, DefaultBotProperties

# Bot token can be obtained via https://t.me/BotFather
TOKEN = "6753603405:AAEXkgfWXPiBr_TGynYIpyCEwEeDg-Ax_Ec"
CHANNEL_ID = -1001824676870

async def main() -> None:
    # Dispatcher is a root router
    dp = Dispatcher()
    # Register all the routers from handlers package
    dp.include_routers(
        start_router,
    )

    # Initialize Bot instance with a default parse mode using DefaultBotProperties
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Start polling
    await dp.start_polling(bot)

    # Send a message to the specified channel indicating that the bot is now alive
    await bot.send_message(chat_id=CHANNEL_ID, text="Bot is now alive!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
