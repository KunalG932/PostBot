# cloning
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
from aiogram.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup

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
            [KeyboardButton(text="Make Post"), KeyboardButton(text="Clone"), KeyboardButton(text="Quote")],
            [KeyboardButton(text="🔙 Back")]
        ],
        resize_keyboard=True,
    )

    # Send the options for creating a post
    await message.answer(
        "Choose an option to create a post:",
        reply_markup=keyboard,
    )

# Inside the message handler for the "Back" button
@router.message(lambda message: message.text == "🔙 Back")
async def cmd_back(message: types.Message):
    # Reset the state for the user to cancel the cloning process
    user_input_dict.get(message.from_user.id, {})["state"] = "main_menu"

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

# Inside the message handler for the text input
@router.message(lambda message: message.text == "Make Post")
async def cmd_text_input(message: types.Message):
    # Ask for text input
    await message.answer("Please provide the text for your post.")

    # Store the user's ID as the key and initialize an empty string as the value
    user_input_dict[message.from_user.id] = {"text": "", "media": None, "inline_buttons": None}

# Inside the message handler for processing text input
@router.message(lambda message: message.from_user.id in user_input_dict and user_input_dict[message.from_user.id]["text"] == "")
async def process_text_input(message: types.Message):
    # Check if the message contains media
    if message.photo:
        # If it's a photo, extract the largest photo available and its file ID
        photo = message.photo[-1]  # Get the largest photo
        media = [InputMediaPhoto(media=photo.file_id, caption=message.caption)]
        user_input_dict[message.from_user.id]["media"] = media
    elif message.document:
        # Handle other types of media like documents, videos, etc. if needed
        pass

    # Retrieve the text input from the message
    post_text = message.text

    # Save the text in the dictionary using the user's ID as the key
    user_input_dict[message.from_user.id]["text"] = post_text

    # Ask if the user wants to add inline buttons
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Yes, add inline buttons"), KeyboardButton(text="No, skip")]],
        resize_keyboard=True,
    )

    await message.answer("Text saved! Do you want to add inline buttons to your post?", reply_markup=keyboard)

# Inside the message handler for choosing whether to add inline buttons or not
@router.message(lambda message: message.text in ["Yes, add inline buttons", "No, skip"])
async def process_inline_buttons_choice(message: types.Message):
    if message.text == "Yes, add inline buttons":
        await message.answer("Please provide the inline buttons in the following format:\n\n"
                             "Example:\n"
                             "[Button1 text + Button1 link]\n"
                             "[Button2 text + Button2 link]\n\n"
                             "To add multiple buttons in one row, write links next to the previous ones.")
    else:
        await post_or_cancel(message)

# Inside the message handler for processing inline buttons input
# Inside the message handler for processing inline buttons input
# Inside the message handler for processing inline buttons input
@router.message(lambda message: user_input_dict.get(message.from_user.id, {}).get("text") != "" and user_input_dict.get(message.from_user.id, {}).get("inline_buttons") is None)
async def process_inline_buttons_input(message: types.Message):
    # Retrieve the inline buttons input from the message
    inline_buttons_input = message.text

    # Split the input by newline characters to get individual button texts with links
    button_lines = inline_buttons_input.split("\n")

    # Create an InlineKeyboardMarkup object to store the inline buttons
    inline_keyboard = InlineKeyboardMarkup()

    for line in button_lines:
        # Split each line by " - " to separate the button text from the link
        parts = line.split(" - ")
        if len(parts) == 2:
            button_text, button_link = parts
            # Create an InlineKeyboardButton object with the provided text and link
            inline_button = InlineKeyboardButton(text=button_text, url=button_link)
            # Add the button to the InlineKeyboardMarkup
            inline_keyboard.add(inline_button)

    # Save the inline keyboard in the dictionary using the user's ID as the key
    user_input_dict[message.from_user.id]["inline_buttons"] = inline_keyboard

    await post_or_cancel(message)

# Function to handle post or cancel options
async def post_or_cancel(message: types.Message):
    # Provide a keyboard with "POST" and "CANCEL" buttons
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📬 POST"), KeyboardButton(text="🚫 CANCEL")]],
        resize_keyboard=True,
    )

    await message.answer("Inline buttons added! Click the 'POST' button to post it in the connected chat or click 'CANCEL' to cancel the post.", reply_markup=keyboard)

# Inside the message handler for posting or canceling
@router.message(lambda message: message.text in ["📬 POST", "🚫 CANCEL"])
async def cmd_post_cancel(message: types.Message):
    if message.text == "📬 POST":
        # Retrieve the saved text, media, and inline buttons from the dictionary
        post_text = user_input_dict.get(message.from_user.id, {}).get("text")
        post_media = user_input_dict.get(message.from_user.id, {}).get("media")
        inline_buttons = user_input_dict.get(message.from_user.id, {}).get("inline_buttons")

        # Check if either text or media is present
        if post_text or post_media:
            # Retrieve the connected chat ID from the user's information
            user_info = await db.users.find_one({"user_id": message.from_user.id})
            connected_chat = user_info.get("connected_chat")

            if connected_chat:
                try:
                    # If media is present, send it along with the text
                    if post_media:
                        await message.bot.send_media_group(chat_id=connected_chat, media=post_media)
                    if post_text:
                        # If inline buttons are provided, send them with the message
                        if inline_buttons:
                            await message.bot.send_message(chat_id=connected_chat, text=post_text, reply_markup=types.InlineKeyboardMarkup().parse(inline_buttons))
                        else:
                            await message.bot.send_message(chat_id=connected_chat, text=post_text)
                    await message.answer("Message posted successfully!")
                except Exception as e:
                    await message.answer(f"Error posting message: {e}")
            else:
                await message.answer("You are not currently connected to any chat. Use /connect to connect to a chat.")
        else:
            await message.answer("No text found. Please provide either text or media to post first.")

        # Remove the user's ID from the dictionary
        del user_input_dict[message.from_user.id]
    elif message.text == "🚫 CANCEL":
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
    # Create a keyboard with options: "Normal Clone" and "Forward Clone"
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Normal Clone"), KeyboardButton(text="Forward Clone")],
            [KeyboardButton(text="🔙 Back")]
        ],
        resize_keyboard=True,
    )

    await message.answer(
        "Choose an option for cloning:",
        reply_markup=keyboard,
    )

# Inside the message handler for selecting "Normal Clone"
@router.message(lambda message: message.text == "Normal Clone")
async def cmd_normal_clone(message: types.Message):
    # Set the cloning state for the user
    user_input_dict.setdefault(message.from_user.id, {})["state"] = "normal_cloning"

    # Ask for the message to clone
    await message.answer("Please send the message you want to clone.")

# Inside the message handler for selecting "Forward Clone"
@router.message(lambda message: message.text == "Forward Clone")
async def cmd_forward_clone(message: types.Message):
    try:
        # Set the cloning state for the user
        user_input_dict.setdefault(message.from_user.id, {})["state"] = "forward_cloning"

        # Send a message asking the user to provide the message they want to clone
        await message.answer("Please send the message you want to clone.")

    except Exception as e:
        await message.answer(f"Error initiating forward clone: {e}")

# Inside the message handler for receiving the message to clone (forward clone)
@router.message(lambda message: user_input_dict.get(message.from_user.id, {}).get("state") == "forward_cloning")
async def process_forward_clone_message(message: types.Message):
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

# Inside the message handler for receiving the message to clone
@router.message(lambda message: user_input_dict.get(message.from_user.id, {}).get("state") == "normal_cloning")
async def process_normal_clone_message(message: types.Message):
    try:
        # Retrieve the connected chat from the user's information
        user_info = await db.users.find_one({"user_id": message.from_user.id})
        connected_chat = user_info.get("connected_chat")

        if connected_chat:
            # Clone the message with reply markup (including inline buttons)
            cloned_message = await message.copy_to(chat_id=connected_chat, reply_markup=message.reply_markup)
            await message.answer("Message cloned and sent successfully!")
        else:
            await message.answer("You are not currently connected to any chat. Use /connect to connect to a chat.")
    except Exception as e:
        await message.answer(f"Error cloning message: {e}")

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
