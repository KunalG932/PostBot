"""
Text input processing
"""
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
    
    await message.answer(
        f"**Text Added!**\n\n"
        f"Preview: {message.text[:100]}{'...' if len(message.text) > 100 else ''}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    from .post_menu import show_post_menu
    await show_post_menu(message)
