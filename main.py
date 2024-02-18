import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties  # Add this import
from pymongo import MongoClient

# Set your Telegram bot token here
API_TOKEN = '6753603405:AAEXkgfWXPiBr_TGynYIpyCEwEeDg-Ax_Ec'

# Channel ID where the bot will send a message on startup
CHANNEL_ID = -1001824676870

# MongoDB connection details
MONGO_URI = 'mongodb+srv://exp69:exp69@cluster0.kr93qbe.mongodb.net/?retryWrites=true&w=majority'
MONGO_DB = 'PostBot'
MONGO_COLLECTION = 'users'

# Initialize MongoDB client
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
user_collection = db[MONGO_COLLECTION]

# Initialize Bot instance with default properties
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Initialize Dispatcher with the Bot instance
dp = Dispatcher(bot)

# Command to show stats
@dp.message_handler(Command('stats'))
async def show_stats(message: types.Message):
    total_users = user_collection.count_documents({})
    await message.reply(f"Total users: {total_users}")

# Message handler for any text message
@dp.message_handler()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    user_collection.update_one({'_id': user_id}, {'$setOnInsert': {'_id': user_id}}, upsert=True)

    # Echo the received message
    await message.reply(message.text)

# Send a message to the channel on bot startup
async def on_startup(dp):
    await bot.send_message(chat_id=CHANNEL_ID, text="Bot is now alive!")

# Updated main function
async def main() -> None:
    # And the run events dispatching
    dp.run_polling(bot, on_startup=on_startup, skip_updates=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
