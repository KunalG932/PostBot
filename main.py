import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient  # Import Motor library for MongoDB

from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from aiogram.dispatcher import DefaultRouter, filters

# Bot token can be obtained via https://t.me/BotFather
TOKEN = "6753603405:AAEXkgfWXPiBr_TGynYIpyCEwEeDg-Ax_Ec"
CHANNEL_ID = -1001824676870

# MongoDB connection parameters
MONGO_URI = "mongodb+srv://exp69:exp69@cluster0.kr93qbe.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "Postbot"

# Initialize MongoDB client
mongo_client = AsyncIOMotorClient(MONGO_URI)
mongo_db = mongo_client[DB_NAME]

# Define a collection for storing user data
users_collection = mongo_db["users"]

async def insert_user(user_id):
    # Insert user ID into the MongoDB users collection
    await users_collection.update_one({"_id": user_id}, {"$set": {"_id": user_id}}, upsert=True)

async def insert_channel(channel_id):
    # Insert channel ID into the MongoDB channels collection
    # You can customize this function based on your data structure
    pass

async def get_stats():
    # Retrieve the total number of users and channels from MongoDB
    total_users = await users_collection.count_documents({})
    total_channels = await channels_collection.count_documents({})
    return total_users, total_channels

# Define a router for handling /stats command
stats_router = DefaultRouter()

@stats_router.message(filters.Command("stats"))
async def command_stats_handler(message: types.Message):
    total_users, total_channels = await get_stats()
    await message.answer(f"Total Users: {total_users}\nTotal Channels: {total_channels}")

async def main() -> None:
    # Dispatcher is a root router
    dp = Dispatcher()
    dp.middleware.setup(LoggingMiddleware())

    # Register routers
    dp.include_router(stats_router)
    
    # Initialize Bot instance with a default parse mode using DefaultBotProperties
    bot = Bot(TOKEN, default=types.DefaultBot)

    # Start polling
    await dp.start_polling(bot)

    # Send a message to the specified channel indicating that the bot is now alive
    await bot.send_message(chat_id=CHANNEL_ID, text="Bot is now alive!", parse_mode=ParseMode.HTML)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
