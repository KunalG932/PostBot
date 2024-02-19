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

dp = Dispatcher()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Create a custom keyboard with only "Create Post" button
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌟 Create Post 🌟")],
            [KeyboardButton(text="Chat")]
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
            [KeyboardButton(text="🌟 Create Post 🌟")],
            [KeyboardButton(text="Chat")]
        ],
        resize_keyboard=True,
    )

    await message.answer("Hello, <b>{}</b> !\nYou can use the following options:".format(message.from_user.full_name), reply_markup=keyboard, parse_mode=ParseMode.HTML)

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    total_users = await db.users.count_documents({})
    await message.reply(f"Total users: {total_users}")

# Add a handler for processing the provided chat ID or username and connecting
# Handler for the "Chat" button
@router.message(lambda message: message.text == "Chat")
async def cmd_chat(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Connect"), KeyboardButton(text="Connected")],
            [KeyboardButton(text="🔙 Back")]
        ],
        resize_keyboard=True,
    )

    await message.answer(
        "Choose an option:",
        reply_markup=keyboard,
    )

# Handler for processing the provided username or chat ID and connecting
@router.message(lambda message: message.text.startswith("Connect"))
async def cmd_connect_channel(message: types.Message):
    try:
        # Extract the channel username or chat ID from the message text
        channel_parts = message.text.split(maxsplit=1)

        if len(channel_parts) > 1:
            channel_identifier = channel_parts[1].strip()
            print("Received channel identifier:", channel_identifier)

            try:
                # Check if the identifier is a chat ID (numeric)
                chat_id = int(channel_identifier)
            except ValueError:
                # If not numeric, assume it's a username
                chat_id = channel_identifier

            print("Processed chat ID:", chat_id)

            try:
                # Get information about the chat
                chat_info = await message.bot.get_chat(chat_id)

                # Check if the bot is an administrator in the chat
                if not chat_info.permissions.can_invite_users:
                    await message.reply("Bot must be an admin in the chat to connect. Please promote the bot and try again.")
                    return
            except types.ChatNotFound:
                await message.reply("Chat not found. Please make sure the chat exists and the bot has access to it.")
                return
            except Exception as e:
                await message.reply(f"An error occurred: {e}")
                return

            # Update user information with connected chat
            await db.users.update_one(
                {"user_id": message.from_user.id},
                {"$set": {"connected_chat": chat_id}},
                upsert=True
            )

            await message.reply(f"You have successfully connected to the chat: {chat_id}")
        else:
            # Ask the user to provide the username or chat ID
            await message.reply("Please provide the username or chat ID of the channel to connect.")
    except Exception as e:
        print(f"An error occurred during connect command: {e}")
        await message.reply(f"An error occurred: {e}")

@router.message(lambda message: message.text == "Connected")
async def cmd_connected_from_chat(message: types.Message):
    # Retrieve connected chat from the user's information
    user_info = await db.users.find_one({"user_id": message.from_user.id})

    if user_info:
        connected_chat = user_info.get("connected_chat")

        if connected_chat:
            await message.reply(f"You are currently connected to the chat: {connected_chat}")
        else:
            await message.reply("You are not currently connected to any chat. Use /connect to connect to a chat.")
    else:
        await message.reply("You are not currently connected to any chat. Use /connect to connect to a chat.")

async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    dp.include_routers(router)

    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await mongo_client.admin.command("ismaster")

    await dp.start_polling(bot)
    await bot.send_message(chat_id=CHANNEL_ID, text="Bot is now alive!")

if __name__ == "__main__":
    asyncio.run(main())
