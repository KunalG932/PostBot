"""
Media handling functionality
"""
from aiogram import types
from aiogram.enums import ParseMode

from constants import router
from utils.data_store import get_user_data, set_user_data
from utils.keyboards import get_media_management_keyboard

@router.message(lambda message: message.text == "Clear Media")
async def cmd_clear_media(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if user_data:
        user_data["media"] = []
        set_user_data(message.from_user.id, user_data)
        await message.answer("All media cleared!")
        
    from .post_creation import cmd_add_media
    await cmd_add_media(message)

@router.message(lambda message: message.text == "Done Adding Media")
async def cmd_done_adding_media(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if user_data:
        user_data["state"] = "main_post_menu"
        set_user_data(message.from_user.id, user_data)
        media_count = len(user_data["media"])
        await message.answer(f"Media added! ({media_count} files)")
    
    from .post_menu import show_post_menu
    await show_post_menu(message)

# Handler for processing media input (photos, videos, documents)
@router.message(lambda message: 
    get_user_data(message.from_user.id).get("state") == "adding_media" and
    (message.photo or message.video or message.document) and
    message.text not in ["Clear Media", "Done Adding Media", "Back to Post Menu"]
)
async def process_media_input(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    media_item = None
    
    if message.photo:
        # Get the largest photo size
        largest_photo = max(message.photo, key=lambda x: x.file_size or 0)
        media_item = {
            "type": "photo",
            "file_id": largest_photo.file_id,
            "caption": message.caption or ""
        }
    elif message.video:
        media_item = {
            "type": "video",
            "file_id": message.video.file_id,
            "caption": message.caption or ""
        }
    elif message.document:
        media_item = {
            "type": "document",
            "file_id": message.document.file_id,
            "caption": message.caption or ""
        }
    
    if media_item:
        user_data["media"].append(media_item)
        set_user_data(message.from_user.id, user_data)
        media_count = len(user_data["media"])
        
        await message.answer(
            f"**Media Added!**\n\n"
            f"Total media files: {media_count}\n"
            f"You can send more media or click 'Done Adding Media' when finished.",
            parse_mode=ParseMode.MARKDOWN
        )
