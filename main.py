import asyncio
import logging
import motor.motor_asyncio
from aiogram import Router
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.types.chat_member_updated import ChatMemberUpdated
from aiogram.client.default import DefaultBotProperties # Add this import

TOKEN = "6753603405:AAEXkgfWXPiBr_TGynYIpyCEwEeDg-Ax_Ec"
CHANNEL_ID = -1001824676870
MONGO_URI = "mongodb+srv://exp69:exp69@cluster0.kr93qbe.mongodb.net/?retryWrites=true&w=majority"

mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = mongo_client["Postbot"]  # Replace with your desired database name

start_router = Router()
stats_router = Router()

@start_router.message(Command("start"))
async def cmd_start(event: types.Message):
    # Insert user ID into the database
    await event.answer(f"Hello, <b>{event.from_user.full_name}!</b>")
    await db.users.update_one(
        {"user_id": event.from_user.id},
        {"$set": {"user_id": event.from_user.id}},
        upsert=True
    )
    
    # Your existing start command logic here...

@stats_router.message(Command("stats"))
async def cmd_stats(event: types.Message):
    # Count total users
    total_users = await db.users.count_documents({})
    
    # Count total channels/groups
    total_channels = await db.channels.count_documents({})

    # Send the stats message
    await event.reply(f"Total users: {total_users}\nTotal channels/groups: {total_channels}")

@stats_router.message(ChatMemberUpdated)
async def new_chat_members(event: types.Message):
    for member in event.new_chat_members:
        # Check if the bot is added to a group or channel
        if member.user.id == event.bot.id:
            # Insert channel ID into the database
            await db.channels.update_one(
                {"channel_id": event.chat_id},  # Fix here: use event.chat_id instead of event.chat.id
                {"$set": {"channel_id": event.chat_id}},
                upsert=True
            )

async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(stats_router)

    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await mongo_client.admin.command("ismaster")

    await dp.start_polling(bot)
    await bot.send_message(chat_id=CHANNEL_ID, text="Bot is now alive!")

if __name__ == "__main__":
    asyncio.run(main())
