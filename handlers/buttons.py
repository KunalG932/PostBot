"""
Button management handlers
"""
import re
import html
from aiogram import types
from aiogram.enums import ParseMode

from constants import router
from utils.data_store import get_user_data, set_user_data
from utils.keyboards import get_back_to_post_menu_keyboard

@router.message(lambda message: message.text == "Add New Button")
async def cmd_add_new_button(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        from .post_creation import cmd_create_post
        await cmd_create_post(message)
        return
    
    user_data["state"] = "adding_button_text"
    set_user_data(message.from_user.id, user_data)
    
    keyboard = get_back_to_post_menu_keyboard()
    
    await message.answer(
        f"<b>Add New Button</b>\n\n"
        f"Send me the text for the button:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@router.message(lambda message: message.text == "Send Message Format")
async def cmd_send_message_format(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        from .post_creation import cmd_create_post
        await cmd_create_post(message)
        return
    
    user_data["state"] = "adding_multiple_buttons"
    set_user_data(message.from_user.id, user_data)
    
    keyboard = get_back_to_post_menu_keyboard()
    
    await message.answer(
        f"<b>Send Multiple Buttons Format</b>\n\n"
        f"Send buttons in this format:\n"
        f"<code>Button1 - https://url1.com | Button2 - https://url2.com</code>\n\n"
        f"<b>Examples:</b>\n"
        f"• <code>Visit Website - https://example.com</code>\n"
        f"• <code>Download App - https://app.com | Join Channel - https://t.me/channel</code>\n"
        f"• <code>Button1 - url1 | Button2 - url2 | Button3 - url3</code>\n\n"
        f"Use <code> | </code> to separate multiple buttons.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@router.message(lambda message: message.text == "Clear Buttons")
async def cmd_clear_buttons(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if user_data:
        user_data["buttons"] = []
        set_user_data(message.from_user.id, user_data)
        await message.answer("All buttons cleared!")
        
    from .post_creation import cmd_add_buttons
    await cmd_add_buttons(message)

# Handler for processing button text input
@router.message(lambda message: 
    get_user_data(message.from_user.id).get("state") == "adding_button_text" and
    message.text and
    message.text not in ["Back to Post Menu"]
)
async def process_button_text_input(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    user_data["temp_button_text"] = message.text
    user_data["state"] = "adding_button_url"
    set_user_data(message.from_user.id, user_data)
    
    keyboard = get_back_to_post_menu_keyboard()
    
    safe_text = html.escape(message.text)
    await message.answer(
        f"<b>Button Text Set:</b> {safe_text}\n\n"
        f"Now send me the URL for this button:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

# Handler for processing button URL input
@router.message(lambda message: 
    get_user_data(message.from_user.id).get("state") == "adding_button_url" and
    message.text and
    message.text not in ["Back to Post Menu"]
)
async def process_button_url_input(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    url = message.text.strip()
    
    # Basic URL validation
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    
    # Validate URL format
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        await message.answer(
            "<b>Invalid URL</b>\n\n"
            "Please send a valid URL (e.g., https://example.com)",
            parse_mode=ParseMode.HTML
        )
        return
    
    button_text = user_data["temp_button_text"]
    user_data["buttons"].append({
        "text": button_text,
        "url": url
    })
    
    # Clean up temp data
    del user_data["temp_button_text"]
    user_data["state"] = "main_post_menu"
    set_user_data(message.from_user.id, user_data)
    
    button_count = len(user_data["buttons"])
    safe_text = html.escape(button_text)
    
    await message.answer(
        f"<b>Button Added!</b>\n\n"
        f"Button: {safe_text}\n"
        f"URL: {url}\n\n"
        f"Total buttons: {button_count}",
        parse_mode=ParseMode.HTML
    )
    
    from .post_menu import show_post_menu
    await show_post_menu(message)

# Handler for processing multiple buttons format
@router.message(lambda message: 
    get_user_data(message.from_user.id).get("state") == "adding_multiple_buttons" and
    message.text and
    message.text not in ["Back to Post Menu"]
)
async def process_multiple_buttons_input(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    text = message.text.strip()
    
    try:
        # Parse the format: Button1 - URL1 | Button2 - URL2
        button_pairs = text.split('|')
        parsed_buttons = []
        
        for pair in button_pairs:
            pair = pair.strip()
            if ' - ' in pair:
                button_text, url = pair.split(' - ', 1)
                button_text = button_text.strip()
                url = url.strip()
                
                # Basic URL validation
                if not (url.startswith("http://") or url.startswith("https://")):
                    url = "https://" + url
                
                # Validate URL format
                url_pattern = re.compile(
                    r'^https?://'  # http:// or https://
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                    r'localhost|'  # localhost...
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                    r'(?::\d+)?'  # optional port
                    r'(?:/?|[/?]\S+)$', re.IGNORECASE)
                
                if url_pattern.match(url):
                    parsed_buttons.append({
                        "text": button_text,
                        "url": url
                    })
                else:
                    safe_text = html.escape(button_text)
                    await message.answer(
                        f"<b>Invalid URL format for button:</b> {safe_text}\n"
                        f"URL: {url}\n\n"
                        f"Please check the format and try again.",
                        parse_mode=ParseMode.HTML
                    )
                    return
            else:
                safe_pair = html.escape(pair)
                await message.answer(
                    f"<b>Invalid format for:</b> {safe_pair}\n\n"
                    f"Use format: Button Text - URL\n"
                    f"Example: Visit Site - https://example.com",
                    parse_mode=ParseMode.HTML
                )
                return
        
        if parsed_buttons:
            # Add all parsed buttons to user data
            user_data["buttons"].extend(parsed_buttons)
            user_data["state"] = "main_post_menu"
            set_user_data(message.from_user.id, user_data)
            
            buttons_summary = "\n".join([f"• {html.escape(btn['text'])} → {btn['url']}" for btn in parsed_buttons])
            total_buttons = len(user_data["buttons"])
            
            await message.answer(
                f"<b>{len(parsed_buttons)} Button(s) Added!</b>\n\n"
                f"Added buttons:\n{buttons_summary}\n\n"
                f"Total buttons: {total_buttons}",
                parse_mode=ParseMode.HTML
            )
            
            from .post_menu import show_post_menu
            await show_post_menu(message)
        else:
            await message.answer(
                "<b>No valid buttons found</b>\n\n"
                "Please check the format and try again.",
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        await message.answer(
            f"<b>Error parsing buttons</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"Please use the correct format:\n"
            f"<code>Button1 - URL1 | Button2 - URL2</code>",
            parse_mode=ParseMode.HTML
        )
