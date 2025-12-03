"""
Post settings handlers (pin, notifications, link preview)
"""
from aiogram import types
from aiogram.enums import ParseMode

from constants import router
from utils.data_store import get_user_data, set_user_data

@router.message(lambda message: message.text == "Pin Post")
async def cmd_toggle_pin(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        from .post_creation import cmd_create_post
        await cmd_create_post(message)
        return
    
    user_data["pin_post"] = not user_data["pin_post"]
    set_user_data(message.from_user.id, user_data)
    
    pin_status = "ON" if user_data["pin_post"] else "OFF"
    
    await message.answer(
        f"**Pin Post: {pin_status}**\n\n"
        f"Your post will {'be pinned' if user_data['pin_post'] else 'not be pinned'} in the channel.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Return to main post menu
    from .post_menu import show_post_menu
    await show_post_menu(message)

@router.message(lambda message: message.text == "Toggle Notifications")
async def cmd_toggle_notifications(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        from .post_creation import cmd_create_post
        await cmd_create_post(message)
        return
    
    user_data["notifications"] = not user_data["notifications"]
    set_user_data(message.from_user.id, user_data)
    
    notif_status = "ON" if user_data["notifications"] else "OFF"
    
    await message.answer(
        f"**Notifications: {notif_status}**\n\n"
        f"Members will {'receive' if user_data['notifications'] else 'not receive'} notifications for this post.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Return to main post menu
    from .post_menu import show_post_menu
    await show_post_menu(message)

@router.message(lambda message: message.text == "Link Preview")
async def cmd_toggle_link_preview(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        from .post_creation import cmd_create_post
        await cmd_create_post(message)
        return
    
    user_data["link_preview"] = not user_data["link_preview"]
    set_user_data(message.from_user.id, user_data)
    
    preview_status = "ON" if user_data["link_preview"] else "OFF"
    
    await message.answer(
        f"**Link Preview: {preview_status}**\n\n"
        f"Links in your post will {'show' if user_data['link_preview'] else 'not show'} previews.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Return to main post menu
    from .post_menu import show_post_menu
    await show_post_menu(message)
