"""
Start command handler
"""
from aiogram import types
from aiogram.filters import Command
from aiogram.enums import ParseMode

from constants import router
from db import db
from utils.keyboards import get_main_menu_keyboard

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Create a custom keyboard with only "Create Post" button
    keyboard = get_main_menu_keyboard()

    # Send the welcome message with the custom keyboard
    await message.answer(
        f"Hello, <b>{message.from_user.full_name} !</b>\n"
        "You can use the following options:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )

    # Update user information in the MongoDB database
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"user_id": message.from_user.id}},
        upsert=True,
    )

@router.message(lambda message: message.text == "🔙 Back")
async def cmd_back(message: types.Message):
    # Clear any ongoing post data
    from utils.data_store import clear_user_data
    clear_user_data(message.from_user.id)

    # Re-send the original keyboard after returning
    keyboard = get_main_menu_keyboard()

    await message.answer(
        "Hello, <b>{}</b> !\nYou can use the following options:".format(
            message.from_user.full_name
        ),
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )

@router.message(lambda message: message.text == "✏️ Edit Post")
async def cmd_edit_post_menu(message: types.Message):
    """Handle Edit Post button from main menu"""
    from .edit_post import cmd_edit_post
    await cmd_edit_post(message)
