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

router = Router()

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

@router.message(lambda message: message.text == "Text")
async def cmd_text_option(message: types.Message):
    # Ask the user to provide a text message for the post
    await message.answer("Please provide your text message for the post.")

@router.message(lambda message: message.text.lower() == "yes")
async def cmd_yes_add_buttons(message: types.Message):
    # Provide instructions for adding buttons
    await message.answer(
        "To add buttons, use the following format:\n"
        "[Button text + Button URL]\n"
        "For example:\n"
        "[Translator + https://t.me/TransioBot]\n"
        "[Text + https://example.com]"
    )

@router.message(lambda message: message.text.lower() == "no")
async def cmd_no_add_buttons(message: types.Message):
    # Reply to the user that the post is ready to send to the channel
    await message.answer("Your post is ready to send to the channel!")

@router.message()
async def process_text_message(message: types.Message):
    # Save the user's text as a post
    post_text = message.reply_to_message.text if message.reply_to_message else message.text

    # Check if the post_text contains buttons in the specified format
    if "[button" in post_text.lower():
        # Process buttons and extract them
        buttons = process_buttons(post_text)

        # Send the post with buttons to the channel
        await send_post_with_buttons(message, post_text, buttons)

        # Reply to the user that the post with buttons is ready
        await message.answer("Your post with buttons is ready to send to the channel!")
    else:
        # If no buttons provided, save the post without buttons
        await db.posts.insert_one({"user_id": message.from_user.id, "text": post_text})

        # Reply to the user that the post without buttons is ready
        await message.answer("Your post without buttons is ready to send to the channel!")

# Function to process buttons in the specified format
def process_buttons(post_text):
    # Extract buttons from the post_text
    # Implement your logic to process buttons in the specified format
    # For simplicity, let's assume the buttons are provided in the correct format
    buttons = [button.strip() for button in post_text.split("[") if button]

    return buttons

# Function to send the post with buttons to the channel
async def send_post_with_buttons(message, post_text, buttons):
    # Implement your logic to send the post with buttons to the channel
    # For simplicity, let's assume you have a channel_id variable
    channel_id = CHANNEL_ID

    # Join the buttons and add them to the post_text
    post_with_buttons = f"{post_text}\n\n{' '.join(buttons)}"

    # Send the complete post with buttons to the channel
    await message.bot.send_message(channel_id, post_with_buttons)

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    total_users = await db.users.count_documents({})
    await message.reply(f"Total users: {total_users}")

async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    dp = Dispatcher()
    dp.include_router(router)

    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await mongo_client.admin.command("ismaster")

    await dp.start_polling(bot)
    await bot.send_message(chat_id=CHANNEL_ID, text="Bot is now alive!")

if __name__ == "__main__":
    asyncio.run(main())
