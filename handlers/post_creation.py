"""
Post creation handlers
"""
import html
from aiogram import types
from aiogram.enums import ParseMode

from constants import router
from utils.data_store import get_user_data, set_user_data, init_user_data
from utils.keyboards import (
    get_post_creation_keyboard, 
    get_back_to_post_menu_keyboard,
    get_media_management_keyboard,
    get_button_management_keyboard,
    get_clear_confirmation_keyboard
)

@router.message(lambda message: message.text == "Create Post")
async def cmd_create_post(message: types.Message):
    # Initialize post data for the user
    init_user_data(message.from_user.id)
    
    # Create comprehensive post creation menu
    keyboard = get_post_creation_keyboard()

    # Send the options for creating a post
    await message.answer(
        "<b>Create Your Post</b>\n\n"
        "Choose options to customize your post:\n"
        "• Add text content\n"
        "• Upload media (photos/videos/documents)\n"
        "• Add multiple buttons with custom format\n"
        "• Pin the post in channel\n"
        "• Control notifications\n"
        "• Enable/disable link preview\n\n"
        "Use 'Preview Post' to see how it will look before publishing!",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@router.message(lambda message: message.text == "Add Text")
async def cmd_add_text(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        await cmd_create_post(message)
        return
    
    user_data["state"] = "adding_text"
    set_user_data(message.from_user.id, user_data)
    
    keyboard = get_back_to_post_menu_keyboard()
    
    current_text = user_data["text"]
    preview_text = ""
    if current_text:
        safe_text = html.escape(current_text)
        preview_text = f"\n\n<b>Current text:</b>\n{safe_text}"
    
    await message.answer(
        f"<b>Add Text to Your Post</b>\n\n"
        f"Send me the text you want to include in your post.{preview_text}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@router.message(lambda message: message.text == "Add Media")
async def cmd_add_media(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        await cmd_create_post(message)
        return
    
    user_data["state"] = "adding_media"
    set_user_data(message.from_user.id, user_data)
    
    keyboard = get_media_management_keyboard()
    
    current_media_count = len(user_data["media"])
    
    await message.answer(
        f"<b>Add Media to Your Post</b>\n\n"
        f"Send me photos, videos, or documents to include in your post.\n"
        f"Current media files: {current_media_count}\n\n"
        f"You can send multiple files one by one.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@router.message(lambda message: message.text == "Add Buttons")
async def cmd_add_buttons(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        await cmd_create_post(message)
        return
    
    # Show current buttons if any
    current_buttons = user_data.get("buttons", [])
    buttons_text = ""
    if current_buttons:
        buttons_text = "\n\n<b>Current Buttons:</b>\n"
        for i, btn in enumerate(current_buttons, 1):
            safe_btn_text = html.escape(btn['text'])
            buttons_text += f"{i}. {safe_btn_text} → {btn['url']}\n"
    
    keyboard = get_button_management_keyboard()
    
    await message.answer(
        f"<b>Buttons Management</b>{buttons_text}\n\n"
        f"You can:\n"
        f"• Add individual buttons one by one\n"
        f"• Use message format: Text1 - URL1 | Text2 - URL2\n"
        f"• Clear all buttons\n\n"
        f"Choose an action:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@router.message(lambda message: message.text == "Clear All")
async def cmd_clear_post(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        await cmd_create_post(message)
        return
    
    # Create confirmation keyboard
    keyboard = get_clear_confirmation_keyboard()
    
    await message.answer(
        "<b>Clear All Content?</b>\n\n"
        "WARNING: This will remove all text, media, and buttons from your post.\n"
        "Are you sure you want to continue?",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@router.message(lambda message: message.text == "Yes, Clear All")
async def cmd_confirm_clear_post(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        await cmd_create_post(message)
        return
    
    # Reset post data
    init_user_data(message.from_user.id)
    
    await message.answer(
        "<b>All Content Cleared!</b>\n\nYour post is now empty. You can start fresh!",
        parse_mode=ParseMode.HTML
    )
    
    # Return to main post menu
    from .post_menu import show_post_menu
    await show_post_menu(message)

@router.message(lambda message: message.text == "No, Keep Content")
async def cmd_cancel_clear_post(message: types.Message):
    await message.answer(
        "<b>Content Preserved!</b>\n\nYour post content has been kept.",
        parse_mode=ParseMode.HTML
    )
    from .post_menu import show_post_menu
    await show_post_menu(message)

@router.message(lambda message: message.text == "Back to Post Menu")
async def cmd_back_to_post_menu(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if user_data:
        user_data["state"] = "main_post_menu"
        set_user_data(message.from_user.id, user_data)
    
    from .post_menu import show_post_menu
    await show_post_menu(message)
