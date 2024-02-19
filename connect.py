from aiogram import types
from constants import *
from main import db  # Importing db from main.py

extra_router = Router()

@extra_router.message(Command("connect"))
async def cmd_connect(message: types.Message):
    # Get the channel username from the user's message
    channel_username = message.get_args()

    if not channel_username:
        await message.reply("Please provide the username of the channel to connect.")
        return

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

@extra_router.message(Command("connected"))
async def cmd_connected(message: types.Message):
    # Retrieve connected channel from the user's information
    user_info = await db.users.find_one({"user_id": message.from_user.id})

    if user_info and "connected_channel" in user_info:
        connected_channel = user_info["connected_channel"]
        await message.reply(f"You are currently connected to the channel: {connected_channel}")
    else:
        await message.reply("You are not currently connected to any channel. Use /connect to connect to a channel.")
