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
async def cmd_text_post(message: types.Message):
    await message.answer("Please provide the text for your text post:")

@router.message(lambda message: message.text)
async def process_text_post(message: types.Message):
    text_content = message.text

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Yes"), KeyboardButton(text="No")]
        ],
        resize_keyboard=True,
    )

    await message.answer("Do you want to add buttons to your text post?", reply_markup=keyboard)

@router.message(lambda message: message.text.lower() == "yes")
async def ask_for_button_text(message: types.Message):
    # Ask the user to provide the button text
    await message.answer("Give your button text (e.g., My Button) + [URL]:")

@router.message(lambda message: message.text.lower() == "no")
async def process_no_buttons(message: types.Message):
    await message.answer("This is the content of my text post.\n\nNo buttons added.")

@router.message(lambda message: "+" in message.text and "[" in message.text and "]" in message.text)
async def process_button_text(message: types.Message):
    button_text = message.text

    final_post = f"This is the content of my text post.\n\n{button_text}"
    await message.answer(final_post)

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
