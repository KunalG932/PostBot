import logging
import asyncio
import uvloop  # Import uvloop
import aiogram

from aiogram import Router
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from constants import *
from db import *
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types.sticker import Sticker
from aiogram.types.reaction_type_custom_emoji import ReactionTypeCustomEmoji

user_input_dict = {}

# Set the event loop policy to uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

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
            [KeyboardButton(text="Text"), KeyboardButton(text="Clone"), KeyboardButton(text="Quote")],
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

@router.message(lambda message: message.text == "Text")
async def cmd_text_input(message: types.Message):
    # Ask for text input
    await message.answer("Please provide the text for your post.")

    # Store the user's ID as the key and initialize an empty string as the value
    user_input_dict[message.from_user.id] = ""

@router.message(lambda message: message.from_user.id in user_input_dict and user_input_dict[message.from_user.id] == "")
async def process_text_input(message: types.Message):
    # Retrieve the text input from the message
    post_text = message.text

    # Save the text in the dictionary using the user's ID as the key
    user_input_dict[message.from_user.id] = post_text

    # Provide a keyboard with "POST" and "CANCEL" buttons
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📬 POST"), KeyboardButton(text="🚫 CANCEL")]],
        resize_keyboard=True,
    )

    await message.answer("Text saved! Click the 'POST' button to post it in the connected chat or click 'CANCEL' to cancel the post.", reply_markup=keyboard)

@router.message(lambda message: message.text in ["📬 POST", "🚫 CANCEL"])
async def cmd_post_cancel(message: types.Message):
    # Retrieve the saved text from the dictionary using the user's ID as the key
    post_text = user_input_dict.get(message.from_user.id, "")

    if message.text == "📬 POST":
        if post_text:
            # Retrieve the connected chat ID from the user's information
            user_info = await db.users.find_one({"user_id": message.from_user.id})
            connected_chat = user_info.get("connected_chat")

            if connected_chat:
                # Post the message in the connected chat
                try:
                    await message.bot.send_message(chat_id=connected_chat, text=post_text)
                    await message.answer("Message posted successfully!")
                except Exception as e:
                    await message.answer(f"Error posting message: {e}")
            else:
                await message.answer("You are not currently connected to any chat. Use /connect to connect to a chat.")
        else:
            await message.answer("No text found. Please use the 'Text' option to provide a text message first.")

        # Remove the user's ID from the dictionary
        del user_input_dict[message.from_user.id]
    
    # Optionally, you can provide a response for the "CANCEL" action
    if message.text == "🚫 CANCEL":
        await message.answer("Post canceled!")
        # Remove the user's ID from the dictionary
        del user_input_dict[message.from_user.id]

    # Go back to the "🌟 Create Post 🌟" menu
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌟 Create Post 🌟")],
            [KeyboardButton(text="Chat")]
        ],
        resize_keyboard=True,
    )

    await message.answer("Hello, <b>{}</b> !\nYou can use the following options:".format(message.from_user.full_name), reply_markup=keyboard, parse_mode=ParseMode.HTML)

# Inside the message handler for the "Clone" button
@router.message(lambda message: message.text == "Clone")
async def cmd_clone(message: types.Message):
    # Set the cloning state for the user
    user_input_dict.setdefault(message.from_user.id, {})["state"] = "cloning"

    # Create a custom keyboard with options for normal clone and forward clone
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Normal Clone"), KeyboardButton(text="Forward Clone")],
            [KeyboardButton(text="🔙 Back")]
        ],
        resize_keyboard=True,
    )

    # Ask for the type of clone
    await message.answer("Choose the type of clone:", reply_markup=keyboard)

@router.message(lambda message: message.text in ["Normal Clone", "Forward Clone"])
async def process_clone_type(message: types.Message):
    clone_type = message.text

    if clone_type == "Normal Clone":
        await message.answer("Please send the message you want to clone.")

        # Set the state for normal cloning
        user_input_dict.setdefault(message.from_user.id, {})["clone_type"] = "normal"
    elif clone_type == "Forward Clone":
        await message.answer("Please send the message you want to forward.")

        # Set the state for forward cloning
        user_input_dict.setdefault(message.from_user.id, {})["clone_type"] = "forward"

@router.message(lambda message: user_input_dict.get(message.from_user.id, {}).get("state") == "cloning")
async def process_clone_message(message: types.Message):
    clone_type = user_input_dict.get(message.from_user.id, {}).get("clone_type")

    if clone_type == "normal":
        try:
            # Retrieve the connected chat from the user's information
            user_info = await db.users.find_one({"user_id": message.from_user.id})
            connected_chat = user_info.get("connected_chat")

            if connected_chat:
                # Clone the message including inline buttons
                cloned_message = await message.copy_to(chat_id=connected_chat, reply_markup=message.reply_markup)
                await message.answer("Message cloned and sent successfully!")
            else:
                await message.answer("You are not currently connected to any chat. Use /connect to connect to a chat.")
        except Exception as e:
            await message.answer(f"Error cloning message: {e}")
    elif clone_type == "forward":
        try:
            # Retrieve the connected chat from the user's information
            user_info = await db.users.find_one({"user_id": message.from_user.id})
            connected_chat = user_info.get("connected_chat")

            if connected_chat:
                # Forward the entire message to the connected chat
                await message.forward(chat_id=connected_chat)
                await message.answer("Message forwarded successfully!")
            else:
                await message.answer("You are not currently connected to any chat. Use /connect to connect to a chat.")
        except Exception as e:
            await message.answer(f"Error forwarding message: {e}")

    # Reset the state for the user
    user_input_dict.get(message.from_user.id, {})["state"] = "main_menu"

@router.message(lambda message: message.text == "🌟 Create Post 🌟")
async def cmd_create_post(message: types.Message):
    # Reset the state for the user
    user_input_dict[message.from_user.id] = {"state": "main_menu", "cloning": False}

    # Create a custom keyboard with options
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

@router.message(lambda message: message.text == "Connect")
async def cmd_connect(message: types.Message):
    await message.answer("use command /connect username or chat ID of the channel to connect.\n Example: /connect @ProjectCodeXsupport or /connect -1001511142636")

@router.message(Command("connect"))
async def cmd_connect(message: types.Message):
    # Get the command arguments from the message text
    command_args = message.text.split(maxsplit=1)

    if len(command_args) < 2:
        await message.reply("Please provide the username or chat ID of the channel to connect.")
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

        # Check if the bot is an administrator in the chat
        bot_member = await message.bot.get_chat_member(chat_id, message.bot.id)
        if not bot_member.status in ['administrator', 'creator']:
            await message.reply("Bot must be an admin in the chat to connect. Please promote the bot and try again.")
            return
    except aiogram.exceptions.TelegramBadRequest as e:
        if "chat not found" in str(e).lower():
            await message.reply("Chat not found. Please make sure the chat exists and the bot has access to it.")
        else:
            await message.reply(f"An error occurred: {e}")
        return
    except Exception as e:
        await message.reply(f"An unexpected error occurred: {e}")
        return

    # Update user information with connected chat
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"connected_chat": chat_id}},
        upsert=True
    )

    await message.reply(f"You have successfully connected to the chat: {chat_id}")

async def get_chat_usernames(user_id):
    # Retrieve connected chat from the user's information
    user_info = await db.users.find_one({"user_id": user_id})

    if user_info:
        connected_chat = user_info.get("connected_chat")

        if connected_chat:
            # Query the MongoDB database to get the chat username based on the chat ID
            chat_info = await db.chats.find_one({"chat_id": connected_chat})

            if chat_info:
                # Extract the chat username from the chat information
                chat_username = chat_info.get("chat_username")

                if chat_username:
                    return [chat_username]

    return []

@router.message(lambda message: message.text == "Connected")
async def cmd_connected_from_chat(message: types.Message):
    # Retrieve connected chat from the user's information
    user_info = await db.users.find_one({"user_id": message.from_user.id})

    if user_info:
        connected_chat = user_info.get("connected_chat")

        if connected_chat:
            # Get the list of chat usernames dynamically
            chat_usernames = await get_chat_usernames(message.from_user.id)

            # Create a keyboard with chat usernames and disconnect option
            keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=username) for username in chat_usernames],
                          [KeyboardButton(text="Disconnect")],
                          [KeyboardButton(text="🔙 Back")]],
                resize_keyboard=True,
            )

            await message.reply("You are currently connected to the chat: {}".format(connected_chat),
                                reply_markup=keyboard)
        else:
            await message.reply("You are not currently connected to any chat. Use /connect to connect to a chat.")
    else:
        await message.reply("You are not currently connected to any chat. Use /connect to connect to a chat.")

@router.message(lambda message: message.text == "Disconnect")
async def cmd_disconnect(message: types.Message):
    # Update user information to disconnect from the chat
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$unset": {"connected_chat": ""}},
    )

    # Create a keyboard with the "Back" button
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Back")]],
        resize_keyboard=True,
    )

    await message.reply("You have successfully disconnected from the chat. You can go back to the main menu.",
                        reply_markup=keyboard)

async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    dp.include_routers(router)

    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await mongo_client.admin.command("ismaster")

    await dp.start_polling(bot)
    await bot.send_message(chat_id=CHANNEL_ID, text="Bot is now alive!")

if __name__ == "__main__":
    asyncio.run(main())
