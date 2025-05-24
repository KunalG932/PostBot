"""
Post menu display and management
"""
from aiogram import types
from aiogram.enums import ParseMode

from utils.data_store import get_user_data
from utils.keyboards import get_post_creation_keyboard

async def show_post_menu(message):
    """Helper function to show the main post creation menu"""
    keyboard = get_post_creation_keyboard()
    
    user_data = get_user_data(message.from_user.id)
    
    # Create detailed status summary
    status_lines = []
    
    # Text status
    text_content = user_data.get("text", "")
    if text_content:
        text_preview = text_content[:50] + "..." if len(text_content) > 50 else text_content
        status_lines.append(f"📝 Text: ✅ ({len(text_content)} chars)")
        status_lines.append(f"   Preview: \"{text_preview}\"")
    else:
        status_lines.append("📝 Text: ❌ No text added")
        
    # Media status
    media_list = user_data.get("media", [])
    if media_list:
        media_types = {}
        for media in media_list:
            media_type = media.get("type", "unknown")
            media_types[media_type] = media_types.get(media_type, 0) + 1
        
        type_summary = ", ".join([f"{count} {type_name}" for type_name, count in media_types.items()])
        status_lines.append(f"📷 Media: ✅ ({len(media_list)} files)")
        status_lines.append(f"   Types: {type_summary}")
    else:
        status_lines.append("📷 Media: ❌ No media added")
        
    # Buttons status
    buttons_list = user_data.get("buttons", [])
    if buttons_list:
        status_lines.append(f"🔗 Buttons: ✅ ({len(buttons_list)} buttons)")
        for i, btn in enumerate(buttons_list[:3], 1):  # Show first 3 buttons
            status_lines.append(f"   {i}. {btn['text']}")
        if len(buttons_list) > 3:
            status_lines.append(f"   ... and {len(buttons_list) - 3} more")
    else:
        status_lines.append("🔗 Buttons: ❌ No buttons added")
    
    # Settings status
    settings_icons = []
    if user_data.get("pin_post"):
        settings_icons.append("📌")
    if user_data.get("notifications", True):
        settings_icons.append("🔔")
    if user_data.get("link_preview", True):
        settings_icons.append("🔗")
    
    settings_text = " ".join(settings_icons) if settings_icons else "Default settings"
    status_lines.append(f"⚙️ Settings: {settings_text}")
    
    # Readiness check
    is_ready = bool(text_content or media_list)
    readiness_status = "✅ Ready to publish" if is_ready else "⚠️ Add content to publish"
    
    status_text = "\n".join(status_lines)
    
    await message.answer(
        f"🌟 **Create Your Post** 🌟\n\n"
        f"**Status:**\n{status_text}\n\n"
        f"**{readiness_status}**\n\n"
        f"Choose an option:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
