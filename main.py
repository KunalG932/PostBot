import asyncio
import logging
from os import getenv

from resource.start import start_router

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

# Bot token can be obtained via https://t.me/BotFather
TOKEN = getenv("6753603405:AAEXkgfWXPiBr_TGynYIpyCEwEeDg-Ax_Ec")


async def main() -> None:
    # Dispatcher is a root router
    dp = Dispatcher()
    # Register all the routers from handlers package
    dp.include_routers(
        start_router,
    )

    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
