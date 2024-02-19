import logging
import asyncio
import uvloop  # Import uvloop

from motor.motor_asyncio import AsyncIOMotorClient
from aiogram import Router
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from constants import *

# Set the event loop policy to uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["Postbot"]

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Create a custom keyboard with only "Create Post" button
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌟 Create Post 🌟")]
        ],
        resize_keyboard=True,
    )

    # Send the welcome message with the custom keyboard
    await message.answer(
        f"Hello, <b>{message.from_user.full_name} !</b>\n"
        "You can use the following options:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    # Update user information in the MongoDB database
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"user_id": message.from_user.id}},
        upsert=True
    )

@router.message(lambda message: message.text == "🌟 Create Post 🌟")
async def cmd_create_post(message: types.Message):
    # Create a new keyboard with options: Text, Media, Back
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Text"), KeyboardButton(text="Media"), KeyboardButton(text="Quote")],
            [KeyboardButton(text="🔙 Back")]
        ],
        resize_keyboard=True,
    )

    # Send the options for creating a post
    await message.answer(
        "Choose an option to create a post:",
        reply_markup=keyboard,
    )

@router.message(lambda message: message.text == "🔙 Back")
async def cmd_back(message: types.Message):
    # Re-send the original keyboard after returning
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌟 Create Post 🌟")]
        ],
        resize_keyboard=True,
    )

    await message.answer("Hello, <b>{}</b> !\nYou can use the following options:".format(message.from_user.full_name), reply_markup=keyboard, parse_mode=ParseMode.HTML)

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    total_users = await db.users.count_documents({})
    await message.reply(f"Total users: {total_users}")

@router.message(Command("connect"))
async def cmd_connect(message: types.Message):
    # Get the command arguments from the message text
    command_args = message.get_args()

    if not command_args:
        await message.reply("Please provide the username of the channel to connect.")
        return

    # Extract the channel username from the command arguments
    channel_username = command_args.strip("@")

    try:
        # Get information about the chat (channel)
        chat_info = await message.bot.get_chat(channel_username)

        # Check if the bot is an administrator in the channel
        if not chat_info.permissions.can_invite_users:
            await message.reply("Bot must be an admin in the channel to connect. Please promote the bot and try again.")
            return
    except types.ChatNotFound:
        await message.reply("Channel not found. Please make sure the channel exists and the bot has access to it.")
        return
    except Exception as e:
        await message.reply(f"An error occurred: {e}")
        return

    # Update user information with connected channel
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"connected_channel": channel_username}},
        upsert=True
    )

    await message.reply(f"You have successfully connected to the channel: {channel_username}")

@router.message(Command("connected"))
async def cmd_connected(message: types.Message):
    # Retrieve connected channel from the user's information
    user_info = await db.users.find_one({"user_id": message.from_user.id})

    if user_info and "connected_channel" in user_info:
        connected_channel = user_info["connected_channel"]
        await message.reply(f"You are currently connected to the channel: {connected_channel}")
    else:
        await message.reply("You are not currently connected to any channel. Use /connect to connect to a channel.")

async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    dp = Dispatcher()
    dp.include_routers(router)

    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await mongo_client.admin.command("ismaster")

    await dp.start_polling(bot)
    await bot.send_message(chat_id=CHANNEL_ID, text="Bot is now alive!")

if __name__ == "__main__":
    asyncio.run(main())
