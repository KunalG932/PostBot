"""
Chat connection handlers
"""
import aiogram
from aiogram import types
from aiogram.filters import Command
from aiogram.enums import ParseMode

from constants import router
from db import db
from utils.keyboards import get_chat_menu_keyboard

@router.message(lambda message: message.text == "Chat")
async def cmd_chat(message: types.Message):
    keyboard = get_chat_menu_keyboard()

    await message.answer(
        " **Chat Connection Menu**\n\n"
        "• **Connect**: Connect to a new channel/group\n"
        "• **Connected**: View current connections\n\n"
        "Choose an option:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(lambda message: message.text == "Connect")
async def cmd_connect_info(message: types.Message):
    await message.answer(
        " **Connect to Channel/Group**\n\n"
        "Use the command:\n"
        "`/connect @username` or `/connect channelname`\n\n"
        "**Examples:**\n"
        "• `/connect @ProjectCodeXsupport`\n"
        "• `/connect ProjectCodeXsupport`\n\n"
        "**Multi-Channel Support:**\n"
        "• Connect to multiple channels with separate `/connect` commands\n"
        "• Use `/connected` to view all connected channels\n"
        "• Use `/disconnect @channelname` to remove a channel\n\n"
        "**Note:** The bot must be an admin in the channel/group.",
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(lambda message: message.text == "Connected")
async def cmd_connected_info(message: types.Message):
    # Redirect to the new connected command
    from .connect import cmd_connected
    await cmd_connected(message)

# Note: The /connect command is now handled in connect.py with multi-channel support
# This duplicate function is commented out to avoid conflicts

# @router.message(Command("connect"))
# async def cmd_connect(message: types.Message):
    # Get the command arguments from the message text
    command_args = message.text.split(maxsplit=1)

    if len(command_args) < 2:
        await message.reply(
            " **Invalid Format**\n\n"
            "Please provide the username or chat ID of the channel to connect.\n\n"
            "**Examples:**\n"
            "• `/connect @channelname`\n"
            "• `/connect -1001234567890`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Extract the channel username or chat ID from the command arguments
    channel_identifier = command_args[1].strip()

    try:
        # Check if the identifier is a chat ID (numeric)
        chat_id = int(channel_identifier)
    except ValueError:
        # If not numeric, assume it's a username
        chat_id = channel_identifier

    try:
        # Get information about the chat
        chat_info = await message.bot.get_chat(chat_id)
        chat_name = chat_info.title or chat_info.first_name or str(chat_id)

        # Check if the bot is an administrator in the chat
        bot_member = await message.bot.get_chat_member(chat_id, message.bot.id)
        if not bot_member.status in ["administrator", "creator"]:
            await message.reply(
                f" **Permission Error**\n\n"
                f"Bot must be an admin in **{chat_name}** to connect.\n"
                f"Please promote the bot and try again.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    except aiogram.exceptions.TelegramBadRequest as e:
        if "chat not found" in str(e).lower():
            await message.reply(
                " **Chat Not Found**\n\n"
                "Please make sure:\n"
                "• The chat exists\n"
                "• The bot has access to it\n"
                "• The username/ID is correct",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.reply(
                f" **Error:** {e}",
                parse_mode=ParseMode.MARKDOWN
            )
        return
    except Exception as e:
        await message.reply(
            f" **Unexpected Error:** {e}",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Update user information with connected chat
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"connected_chat": chat_id}},
        upsert=True,
    )

    await message.reply(
        f" **Successfully Connected!**\n\n"
        f"**Connected to:** {chat_name}\n"
        f"**Chat ID:** `{chat_id}`\n\n"
        f"You can now create and publish posts to this chat!",
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(lambda message: message.text == "Connected")
async def cmd_connected_from_chat(message: types.Message):
    # Retrieve connected chat from the user's information
    user_info = await db.users.find_one({"user_id": message.from_user.id})

    if user_info:
        connected_chat = user_info.get("connected_chat")

        if connected_chat:
            try:
                # Get chat information
                chat_info = await message.bot.get_chat(connected_chat)
                chat_name = chat_info.title or chat_info.first_name or str(connected_chat)
                
                # Create keyboard with disconnect option
                from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="Disconnect")],
                        [KeyboardButton(text=" Back")],
                    ],
                    resize_keyboard=True,
                )

                await message.reply(
                    f" **Current Connection**\n\n"
                    f"**Connected to:** {chat_name}\n"
                    f"**Chat ID:** `{connected_chat}`\n"
                    f"**Type:** {chat_info.type}\n\n"
                    f"You can disconnect or go back to the main menu.",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                await message.reply(
                    f" **Connection Status**\n\n"
                    f"**Connected to:** {connected_chat}\n"
                    f"**Note:** Cannot fetch chat details\n\n"
                    f"Error: {str(e)}",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await message.reply(
                " **No Active Connection**\n\n"
                "You are not currently connected to any chat.\n"
                "Use **Connect** to connect to a channel or group.",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await message.reply(
            " **No Active Connection**\n\n"
            "You are not currently connected to any chat.\n"
            "Use **Connect** to connect to a channel or group.",
            parse_mode=ParseMode.MARKDOWN
        )

@router.message(lambda message: message.text == "Disconnect")
async def cmd_disconnect(message: types.Message):
    # Update user information to disconnect from the chat
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$unset": {"connected_chat": ""}},
    )

    # Create a keyboard with the "Back" button
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=" Back")]],
        resize_keyboard=True,
    )

    await message.reply(
        " **Successfully Disconnected**\n\n"
        "You have been disconnected from the chat.\n"
        "You can connect to a new chat anytime.",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
