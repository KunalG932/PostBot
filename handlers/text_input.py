"""
Text input processing
"""
import html
from aiogram import types
from aiogram.enums import ParseMode

from constants import router
from utils.data_store import get_user_data, set_user_data

# Handler for processing text input
@router.message(lambda message: 
    get_user_data(message.from_user.id).get("state") == "adding_text" and
    message.text and
    message.text not in ["Back to Post Menu"]
)
async def process_text_input(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    user_data["text"] = message.text
    user_data["state"] = "main_post_menu"
    set_user_data(message.from_user.id, user_data)
    
    # Escape text for safe preview
    preview_text = html.escape(message.text[:100])
    if len(message.text) > 100:
        preview_text += "..."
    
    await message.answer(
        f"<b>Text Added!</b>\n\n"
        f"Preview: {preview_text}",
        parse_mode=ParseMode.HTML
    )
    
    from .post_menu import show_post_menu
    await show_post_menu(message)
