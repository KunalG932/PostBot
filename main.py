import logging
import asyncio
import uvloop
import aiogram
import html
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

user_input_dict = {}

# Set the event loop policy to uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Decorations
class HtmlDecoration(types.TextDecoration):
    BOLD_TAG = "b"
    ITALIC_TAG = "i"
    UNDERLINE_TAG = "u"
    STRIKETHROUGH_TAG = "s"
    SPOILER_TAG = "tg-spoiler"
    EMOJI_TAG = "tg-emoji"
    BLOCKQUOTE_TAG = "blockquote"

    def link(self, value: str, link: str) -> str:
        return f'<a href="{link}">{value}</a>'

    def bold(self, value: str) -> str:
        return f"<{self.BOLD_TAG}>{value}</{self.BOLD_TAG}>"

    def italic(self, value: str) -> str:
        return f"<{self.ITALIC_TAG}>{value}</{self.ITALIC_TAG}>"

    def code(self, value: str) -> str:
        return f"<code>{value}</code>"

    def pre(self, value: str) -> str:
        return f"<pre>{value}</pre>"

    def pre_language(self, value: str, language: str) -> str:
        return f'<pre><code class="language-{language}">{value}</code></pre>'

    def underline(self, value: str) -> str:
        return f"<{self.UNDERLINE_TAG}>{value}</{self.UNDERLINE_TAG}>"

    def strikethrough(self, value: str) -> str:
        return f"<{self.STRIKETHROUGH_TAG}>{value}</{self.STRIKETHROUGH_TAG}>"

    def spoiler(self, value: str) -> str:
        return f"<{self.SPOILER_TAG}>{value}</{self.SPOILER_TAG}>"

    def quote(self, value: str) -> str:
        return html.escape(value, quote=False)

    def custom_emoji(self, value: str, custom_emoji_id: str) -> str:
        return f'<{self.EMOJI_TAG} emoji-id="{custom_emoji_id}">{value}</tg-emoji>'

    def blockquote(self, value: str) -> str:
        return f"<{self.BLOCKQUOTE_TAG}>{value}</{self.BLOCKQUOTE_TAG}>"


class MarkdownDecoration(types.TextDecoration):
    MARKDOWN_QUOTE_PATTERN: types.Pattern[str] = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")

    def link(self, value: str, link: str) -> str:
        return f"[{value}]({link})"

    def bold(self, value: str) -> str:
        return f"*{value}*"

    def italic(self, value: str) -> str:
        return f"_\r{value}_\r"

    def code(self, value: str) -> str:
        return f"`{value}`"

    def pre(self, value: str) -> str:
        return f"```\n{value}\n```"

    def pre_language(self, value: str, language: str) -> str:
        return f"```{language}\n{value}\n```"

    def underline(self, value: str) -> str:
        return f"__\r{value}__\r"

    def strikethrough(self, value: str) -> str:
        return f"~{value}~"

    def spoiler(self, value: str) -> str:
        return f"||{value}||"

    def quote(self, value: str) -> str:
        return re.sub(pattern=self.MARKDOWN_QUOTE_PATTERN, repl=r"\\\1", string=value)

    def custom_emoji(self, value: str, custom_emoji_id: str) -> str:
        return self.link(value=value, link=f"tg://emoji?id={custom_emoji_id}")

    def blockquote(self, value: str) -> str:
        return "\n".join(f">{line}" for line in value.splitlines())


html_decoration = HtmlDecoration()
markdown_decoration = MarkdownDecoration()

async def format_message(message: str, use_html: bool = True) -> str:
    decoration = html_decoration if use_html else markdown_decoration

    formatted_message = message

    # Apply formatting based on decoration type
    formatted_message = decoration.bold(formatted_message)
    formatted_message = decoration.italic(formatted_message)
    formatted_message = decoration.underline(formatted_message)
    formatted_message = decoration.strikethrough(formatted_message)
    formatted_message = decoration.spoiler(formatted_message)
    formatted_message = decoration.quote(formatted_message)

    # You can add more formatting options based on your requirements

    return formatted_message

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
async def cmd_post(message: types.Message):
    post_text = user_input_dict.get(message.from_user.id, "")
    
    if post_text:
        formatted_text = await format_message(post_text)
        user_info = await db.users.find_one({"user_id": message.from_user.id})
        connected_chat = user_info.get("connected_chat")

        if connected_chat:
            # Post the formatted message in the connected chat
            try:
                await message.bot.send_message(chat_id=connected_chat, text=formatted_text, parse_mode="HTML")
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
