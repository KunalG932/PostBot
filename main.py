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
import logging
from constants import *
from db import *
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums.content_type import ContentType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

user_input_dict = {}

logging.basicConfig(level=logging.INFO)

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

# Message handler for processing incoming messages
@router.message(content_types=[ContentType.PHOTO, ContentType.VIDEO, ContentType.ANIMATION])
async def process_message(message: types.Message):
    try:
        # Check if the message has a caption
        if message.caption:
            # Extract media caption
            media_caption = message.caption

            # Extract entities from caption
            entities = message.caption_entities

            # Initialize variables for formatted content
            formatted_content = media_caption

            # Check if message has entities
            if entities:
                inline_buttons = []

                # Process each entity
                for entity in entities:
                    # Check if entity is URL type
                    if entity.type == 'url':
                        # Extract URL and add to inline buttons
                        inline_buttons.append(f"[{media_caption[entity.offset:entity.offset+entity.length]}]({entity.url})")

                # Concatenate inline buttons with formatted content
                if inline_buttons:
                    formatted_content += '\n\n' + '\n'.join(inline_buttons)

            # Save formatted content in user input dictionary
            user_input_dict[message.from_user.id] = formatted_content

            # Send confirmation message
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("✅ Confirm"))
            await message.answer(f"Post content:\n{formatted_content}\n\nDo you want to post this?", reply_markup=keyboard)
        else:
            await message.answer("Please provide a caption for the media.")
    except Exception as e:
        logging.exception(f"Error processing message: {e}")
        await message.answer("An error occurred while processing your message. Please try again later.")

# Message handler for confirming the post
@router.message(Text(equals="✅ Confirm"))
async def confirm_post(message: types.Message):
    try:
        # Retrieve user's connected chat
        user_info = await db.users.find_one({"user_id": message.from_user.id})
        connected_chat = user_info.get("connected_chat")

        # Retrieve post content from user input dictionary
        post_content = user_input_dict.get(message.from_user.id)

        if connected_chat and post_content:
            # Send post content to connected chat
            await bot.send_message(chat_id=connected_chat, text=post_content)
            await message.answer("Post sent successfully!")
            del user_input_dict[message.from_user.id]  # Remove user's data from input dictionary
        else:
            await message.answer("You are not currently connected to any chat. Use /connect to connect to a chat.")
    except Exception as e:
        logging.exception(f"Error confirming post: {e}")
        await message.answer("An error occurred while confirming your post. Please try again later.")

# Inside the message handler for the "Make Post" button
@router.message(lambda message: message.text == "Make Post")
async def cmd_make_post(message: types.Message):
    # Ask the user to send the content they want to post
    await message.answer("Please send the content you want to post. This can include text, media, and inline formatted text.")

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
