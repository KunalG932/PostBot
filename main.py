import asyncio
import logging

from handlers.start import start_router

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties  # Add this import

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
    await bot.send_message(chat_id=CHANNEL_ID, text="Bot is now alive!", parse_mode=ParseMode.HTML)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
