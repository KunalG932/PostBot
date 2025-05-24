"""
Clone and quote functionality handlers
"""
from aiogram import types
from aiogram.enums import ParseMode

from constants import router
from db import db
from utils.data_store import get_user_data, set_user_data
from utils.keyboards import get_clone_options_keyboard, get_back_to_post_menu_keyboard

@router.message(lambda message: message.text == "📋 Clone")
async def cmd_clone(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        from .post_creation import cmd_create_post
        await cmd_create_post(message)
        return
    
    # Create a keyboard with options: "Normal Clone" and "Forward Clone"
    keyboard = get_clone_options_keyboard()

    await message.answer(
        "📋 **Clone Message**\n\n"
        "Choose cloning method:\n"
        "• **Normal Clone**: Copy message content with formatting\n"
        "• **Forward Clone**: Forward original message as-is",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(lambda message: message.text == "💬 Quote")
async def cmd_quote(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        from .post_creation import cmd_create_post
        await cmd_create_post(message)
        return
    
    user_data["state"] = "quoting"
    set_user_data(message.from_user.id, user_data)
    
    keyboard = get_back_to_post_menu_keyboard()
    
    await message.answer(
        "💬 **Quote Message**\n\n"
        "Forward or send me the message you want to quote.\n"
        "I'll format it as a quoted message in your post.",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(lambda message: message.text == "Normal Clone")
async def cmd_normal_clone(message: types.Message):
    # Set the cloning state for the user
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        from .post_creation import cmd_create_post
        await cmd_create_post(message)
        return
    
    user_data["state"] = "normal_cloning"
    set_user_data(message.from_user.id, user_data)

    # Ask for the message to clone
    await message.answer(
        "📋 **Normal Clone**\n\n"
        "Please send the message you want to clone.\n"
        "I'll copy it with all formatting preserved.",
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(lambda message: message.text == "Forward Clone")
async def cmd_forward_clone(message: types.Message):
    try:
        # Set the cloning state for the user
        user_data = get_user_data(message.from_user.id)
        if not user_data:
            from .post_creation import cmd_create_post
            await cmd_create_post(message)
            return
        
        user_data["state"] = "forward_cloning"
        set_user_data(message.from_user.id, user_data)

        # Send a message asking the user to provide the message they want to clone
        await message.answer(
            "📋 **Forward Clone**\n\n"
            "Please send the message you want to forward.\n"
            "I'll forward it exactly as-is to your connected channel.",
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        await message.answer(f"❌ Error initiating forward clone: {e}")

# Handler for processing quoted messages
@router.message(
    lambda message: get_user_data(message.from_user.id).get("state") == "quoting"
    and message.text not in ["🔙 Back to Post Menu"]
)
async def process_quote_message(message: types.Message):
    try:
        user_data = get_user_data(message.from_user.id)
        quote_text = ""
        
        # Handle different types of messages for quoting
        if message.text:
            quote_text = message.text
        elif message.caption:
            quote_text = message.caption
        else:
            quote_text = "[Media message]"
        
        # Format as quote
        quoted_content = f"❝ {quote_text} ❞"
        
        # Get sender info if available
        sender_name = "Unknown"
        if message.forward_from:
            sender_name = message.forward_from.full_name
        elif message.forward_from_chat:
            sender_name = message.forward_from_chat.title
        elif message.from_user:
            sender_name = message.from_user.full_name
        
        formatted_quote = f"{quoted_content}\n\n— {sender_name}"
        
        # Add to current post text
        current_text = user_data.get("text", "")
        if current_text:
            user_data["text"] = f"{current_text}\n\n{formatted_quote}"
        else:
            user_data["text"] = formatted_quote
        
        user_data["state"] = "main_post_menu"
        set_user_data(message.from_user.id, user_data)
        
        await message.answer(
            "✅ **Quote Added!**\n\n"
            f"Quote preview:\n{formatted_quote[:200]}{'...' if len(formatted_quote) > 200 else ''}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        from .post_menu import show_post_menu
        await show_post_menu(message)
        
    except Exception as e:
        await message.answer(
            f"❌ **Error Processing Quote**\n\n"
            f"Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )
        from .post_menu import show_post_menu
        await show_post_menu(message)

# Handler for receiving the message to clone (forward clone)
@router.message(
    lambda message: get_user_data(message.from_user.id).get("state") == "forward_cloning"
)
async def process_forward_clone_message(message: types.Message):
    try:
        # Retrieve the connected chat from the user's information
        user_info = await db.users.find_one({"user_id": message.from_user.id})
        connected_chat = user_info.get("connected_chat") if user_info else None

        if connected_chat:
            # Forward the entire message to the connected chat
            await message.forward(chat_id=connected_chat)
            await message.answer(
                "✅ **Message Forwarded Successfully!**\n\n"
                "The message has been forwarded to your connected channel.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.answer(
                "❌ **No Connected Chat**\n\n"
                "You are not currently connected to any chat.\n"
                "Use /connect to connect to a channel.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        await message.answer(
            f"❌ **Error Forwarding Message**\n\n"
            f"Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )

    # Reset the state for the user
    user_data = get_user_data(message.from_user.id)
    if user_data:
        user_data["state"] = "main_post_menu"
        set_user_data(message.from_user.id, user_data)

# Handler for receiving the message to clone (normal clone)
@router.message(
    lambda message: get_user_data(message.from_user.id).get("state") == "normal_cloning"
)
async def process_normal_clone_message(message: types.Message):
    try:
        # Retrieve the connected chat from the user's information
        user_info = await db.users.find_one({"user_id": message.from_user.id})
        connected_chat = user_info.get("connected_chat") if user_info else None

        if connected_chat:
            # Clone the message with reply markup (including inline buttons)
            cloned_message = await message.copy_to(
                chat_id=connected_chat, reply_markup=message.reply_markup
            )
            await message.answer(
                "✅ **Message Cloned Successfully!**\n\n"
                "The message has been copied to your connected channel with all formatting preserved.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.answer(
                "❌ **No Connected Chat**\n\n"
                "You are not currently connected to any chat.\n"
                "Use /connect to connect to a channel.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        await message.answer(
            f"❌ **Error Cloning Message**\n\n"
            f"Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )

    # Reset the state for the user
    user_data = get_user_data(message.from_user.id)
    if user_data:
        user_data["state"] = "main_post_menu"
        set_user_data(message.from_user.id, user_data)
