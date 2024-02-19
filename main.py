import logging
import asyncio
import uvloop  # Import uvloop

from motor.motor_asyncio import AsyncIOMotorClient
from aiogram import Router
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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

class PostState(StatesGroup):
    SAVING_MESSAGE = State()
    ADDING_BUTTONS = State()

@router.message(Text(equals="Text"))
async def handle_text_option(message: types.Message, state: FSMContext):
    # Set the state to SAVING_MESSAGE to save the user's message
    await PostState.SAVING_MESSAGE.set()

    # Save the user's message in the state
    await state.update_data(saved_message=message.text)

    # Ask if the user wants to add buttons
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Yes"), KeyboardButton(text="No")]
        ],
        resize_keyboard=True,
    )
    await message.answer("Do you want to add buttons to your message?", reply_markup=keyboard)

@router.message(Text(equals="Yes"), state=PostState.SAVING_MESSAGE)
async def handle_add_buttons(message: types.Message, state: FSMContext):
    # Set the state to ADDING_BUTTONS to handle the button addition
    await PostState.ADDING_BUTTONS.set()

    # Ask the user for the button format
    await message.answer("Provide the button format (e.g., Translator + [https://t.me/TransioBot], text + url):")

@router.message(state=PostState.ADDING_BUTTONS)
async def handle_button_format(message: types.Message, state: FSMContext):
    # Get the saved message from the state
    data = await state.get_data()
    saved_message = data.get("saved_message")

    # Process the button format and create the reply message
    button_format = message.text
    post_message = f"{saved_message}\n\n{button_format}"

    # Create the InlineKeyboardButton based on the provided format
    button_parts = button_format.split("+")
    if len(button_parts) == 2:
        button_text, button_url = button_parts[0].strip(), button_parts[1].strip()
        post_keyboard = InlineKeyboardMarkup().insert(InlineKeyboardButton(text=button_text, url=button_url))
    else:
        post_keyboard = None  # Handle the case where the format is incorrect

    # Reply with the saved message and the button
    await message.reply(post_message, reply_markup=post_keyboard)

    # Reset the state to the initial state
    await state.finish()

@router.message(Text(equals="No"), state=PostState.SAVING_MESSAGE)
async def handle_no_buttons(message: types.Message, state: FSMContext):
    # Get the saved message from the state
    data = await state.get_data()
    saved_message = data.get("saved_message")

    # Reply with the saved message without buttons
    await message.reply(saved_message)

    # Reset the state to the initial state
    await state.finish()

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
