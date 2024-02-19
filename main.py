import asyncio
import logging
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import Message, Chat
from aiogram.enums.chat_type import ChatType
from aiogram.filters import Command

from pymongo import MongoClient

# MongoDB configuration
MONGO_URI = "mongodb+srv://exp69:exp69@cluster0.kr93qbe.mongodb.net/?retryWrites=true&w=majority"
DATABASE_NAME = "Postbot"
USER_COLLECTION_NAME = "users"
GROUP_COLLECTION_NAME = "groups"

# Bot token can be obtained via https://t.me/BotFather
TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_ID = -1001824676870

# Initialize MongoDB client and databases
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]
user_collection = db[USER_COLLECTION_NAME]
group_collection = db[GROUP_COLLECTION_NAME]

# Router for handling start command
start_router = Router()


@start_router.message(ChatType.PRIVATE, Command("start"))
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command in private chat
    """
    user_id = message.from_user.id
    user_collection.update_one({"_id": user_id}, {"$set": {"username": message.from_user.username}}, upsert=True)
    await message.answer(f"Hello, <b>{message.from_user.full_name}!</b>")


@start_router.chat_member(Command("start"))
async def command_start_group_handler(message: Message, chat_member: Chat):
    """
    This handler receives messages with `/start` command in a group or channel
    """
    chat_id = message.chat.id
    group_collection.update_one({"_id": chat_id}, {"$set": {"title": chat_member.title}}, upsert=True)
    await message.reply(f"Hello, {chat_member.title} group member!")


async def stats_command_handler(message: Message):
    """
    This handler receives messages with `/stats` command
    """
    total_users = user_collection.count_documents({})
    total_groups = group_collection.count_documents({})
    await message.answer(f"Total users: {total_users}\nTotal groups: {total_groups}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    dp = Dispatcher()
    dp.include_router(start_router)
    dp.register_message_handler(stats_command_handler, commands="stats")

    bot = Bot(TOKEN)
    dp.run_polling(bot)
