import asyncio
import logging
import motor.motor_asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, ChatMemberUpdated

TOKEN = "6753603405:AAEXkgfWXPiBr_TGynYIpyCEwEeDg-Ax_Ec"
CHANNEL_ID = -1001824676870
MONGO_URI = "mongodb+srv://exp69:exp69@cluster0.kr93qbe.mongodb.net/?retryWrites=true&w=majority"

mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = mongo_client["Postbot"]  # Replace with your desired database name

start_router = Dispatcher()
stats_router = Dispatcher()


@start_router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Insert user ID into the database
    await message.answer(f"Hello, <b>{message.from_user.full_name}!</b>")
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"user_id": message.from_user.id}},
        upsert=True
    )
    
    # Your existing start command logic here...

@start_router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    # Count total users
    total_users = await db.users.count_documents({})
    
    # Count total channels/groups
    total_channels = await db.channels.count_documents({})

    # Send the stats message
    await message.reply(f"Total users: {total_users}\nTotal channels/groups: {total_channels}")


@stats_router.message(ChatMemberUpdated())
async def new_chat_members(message: types.Message):
    # Check if the bot is added to a group or channel
    if bot.id in [user.id for user in message.new_chat_members]:
        # Insert channel ID into the database
        await db.channels.update_one(
            {"channel_id": message.chat.id},
            {"$set": {"channel_id": message.chat.id}},
            upsert=True
        )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    dp = Dispatcher()
    dp.register_router(start_router)
    dp.register_router(stats_router)

    bot = Bot(TOKEN)

    await mongo_client.admin.command("ismaster")

    await dp.start_polling(bot)
    await bot.send_message(chat_id=CHANNEL_ID, text="Bot is now alive!")


if __name__ == "__main__":
    asyncio.run(main())
