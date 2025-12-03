"""
Edit post handler for PostBot
Allows editing existing posts in channels
"""
from aiogram import types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAnimation
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import html

from constants import router
from db import db
from config import Config
from utils.logger import logger, log_user_action

# Simple in-memory storage for edit states
# In a production app, use Redis or database
edit_sessions = {}

def get_user_data(user_id):
    if user_id not in edit_sessions:
        edit_sessions[user_id] = {}
    return edit_sessions[user_id]

def set_user_data(user_id, data):
    edit_sessions[user_id] = data

def clear_user_data(user_id):
    if user_id in edit_sessions:
        del edit_sessions[user_id]

@router.message(Command("edit"))
async def cmd_edit_post(message: types.Message):
    """Start the edit post flow"""
    # Check if user has any connected channels
    user = await db.users.find_one({"user_id": message.from_user.id})
    
    if not user or not user.get("connected_channels"):
        await message.reply(
            "<b>No Connected Channels</b>\n\n"
            "You need to connect a channel first to edit posts.\n"
            "Use <code>/connect</code> to add a channel.",
            parse_mode=ParseMode.HTML
        )
        return
    
    connected_channels = user.get("connected_channels", [])
    
    # Create keyboard with channels
    keyboard = []
    for channel in connected_channels:
        title = channel.get('title', channel.get('username', 'Unknown'))
        # Truncate long titles
        if len(title) > 30:
            title = title[:27] + "..."
            
        callback_data = f"edit_channel_{channel.get('chat_id')}"
        keyboard.append([InlineKeyboardButton(text=title, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton(text="Cancel", callback_data="cancel_edit")])
    
    await message.reply(
        "<b>Edit Post</b>\n\n"
        "Select a channel to edit a post from:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    # Initialize session
    clear_user_data(message.from_user.id)
    set_user_data(message.from_user.id, {"state": "selecting_channel"})

@router.callback_query(lambda query: query.data == "cancel_edit")
async def handle_cancel_edit(query: types.CallbackQuery):
    """Cancel the edit process"""
    clear_user_data(query.from_user.id)
    await query.message.edit_text("Edit cancelled.")
    await query.answer("Cancelled")

@router.callback_query(lambda query: query.data.startswith("edit_channel_"))
async def handle_channel_selection(query: types.CallbackQuery):
    """Handle channel selection for editing"""
    chat_id = query.data.replace("edit_channel_", "")
    
    # Verify user has access to this channel
    user = await db.users.find_one({"user_id": query.from_user.id})
    connected_channels = user.get("connected_channels", [])
    
    selected_channel = None
    for channel in connected_channels:
        if str(channel.get('chat_id')) == str(chat_id):
            selected_channel = channel
            break
    
    if not selected_channel:
        await query.answer("Channel not found in your connected channels.", show_alert=True)
        return
    
    # Save selected channel to session
    user_data = get_user_data(query.from_user.id)
    user_data["selected_channel"] = selected_channel
    user_data["edit_chat_id"] = chat_id
    user_data["state"] = "selecting_post"
    set_user_data(query.from_user.id, user_data)
    
    channel_title = html.escape(selected_channel.get('title', 'Unknown'))
    
    await query.message.edit_text(
        f"<b>Channel: {channel_title}</b>\n\n"
        "Please forward the message you want to edit from this channel to this chat.\n"
        "Or send the link to the post.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back", callback_data="back_to_channels")],
            [InlineKeyboardButton(text="Cancel", callback_data="cancel_edit")]
        ])
    )
    await query.answer()

@router.callback_query(lambda query: query.data == "back_to_channels")
async def handle_back_to_channels(query: types.CallbackQuery):
    """Go back to channel selection"""
    # Re-use the cmd_edit_post logic but editing the message
    user = await db.users.find_one({"user_id": query.from_user.id})
    connected_channels = user.get("connected_channels", [])
    
    keyboard = []
    for channel in connected_channels:
        title = channel.get('title', channel.get('username', 'Unknown'))
        if len(title) > 30:
            title = title[:27] + "..."
        callback_data = f"edit_channel_{channel.get('chat_id')}"
        keyboard.append([InlineKeyboardButton(text=title, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton(text="Cancel", callback_data="cancel_edit")])
    
    await query.message.edit_text(
        "<b>Edit Post</b>\n\n"
        "Select a channel to edit a post from:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    user_data = get_user_data(query.from_user.id)
    user_data["state"] = "selecting_channel"
    set_user_data(query.from_user.id, user_data)

@router.message(lambda message: get_user_data(message.from_user.id).get("state") == "selecting_post")
async def handle_post_input(message: types.Message):
    """Handle the forwarded post or link"""
    user_data = get_user_data(message.from_user.id)
    chat_id = user_data.get("edit_chat_id")
    
    message_id = None
    
    # Check if forwarded
    if message.forward_from_chat:
        if str(message.forward_from_chat.id) == str(chat_id):
            message_id = message.forward_from_message_id
        else:
            await message.reply(
                "<b>Wrong Channel</b>\n\n"
                "This message is forwarded from a different channel.\n"
                "Please forward from the channel you selected.",
                parse_mode=ParseMode.HTML
            )
            return
    
    # Check if link
    elif message.text and "t.me/" in message.text:
        try:
            # Extract message ID from link
            # Format: https://t.me/channelname/123 or https://t.me/c/1234567890/123
            parts = message.text.strip().split('/')
            if parts[-1].isdigit():
                message_id = int(parts[-1])
        except:
            pass
    
    if not message_id:
        await message.reply(
            "<b>Invalid Post</b>\n\n"
            "Could not identify the post.\n"
            "Please forward the message from the channel or send a valid link.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Save message ID
    user_data["edit_message_id"] = message_id
    user_data["state"] = "loading_post"
    set_user_data(message.from_user.id, user_data)
    
    status_msg = await message.reply("Loading post content...")
    
    # Fetch post content (we can't actually fetch content via bot API unless we have it stored)
    # But we can ask the user to confirm what they want to edit
    
    # In a real scenario, we might have the post stored in DB if we created it
    # Or we just start with empty/unknown content and let user overwrite
    
    # Try to find in DB first
    db_post = await db.posts.find_one({
        "channel_id": int(chat_id) if chat_id.lstrip('-').isdigit() else chat_id,
        "message_id": message_id
    })
    
    content = {}
    if db_post:
        content = {
            "text": db_post.get("content", ""),
            "media": db_post.get("media", []),
            "buttons": db_post.get("buttons", [])
        }
    else:
        # If forwarded, we might have content
        if message.forward_from_chat:
            content = {
                "text": message.text or message.caption or "",
                "media": [], # Can't easily get media from forward without downloading
                "buttons": []
            }
    
    user_data["original_content"] = content
    user_data["text"] = content.get("text", "")
    user_data["media"] = content.get("media", [])
    user_data["buttons"] = content.get("buttons", [])
    user_data["state"] = "editing_post"
    set_user_data(message.from_user.id, user_data)
    
    await status_msg.delete()
    await show_post_content_and_edit_options(message, content, user_data.get("selected_channel"))

async def show_post_content_and_edit_options(message, content, channel):
    """Show post content and edit options"""
    text_preview = content.get("text", "")
    if len(text_preview) > 200:
        text_preview = text_preview[:197] + "..."
    
    safe_text_preview = html.escape(text_preview) if text_preview else "<i>No text content</i>"
    channel_title = html.escape(channel.get('title', 'Unknown'))
    
    media_count = len(content.get("media", []))
    buttons_count = len(content.get("buttons", []))
    
    info_text = (
        f"<b>Editing Post</b>\n\n"
        f"<b>Channel:</b> {channel_title}\n"
        f"<b>Message ID:</b> {get_user_data(message.from_user.id).get('edit_message_id')}\n\n"
        f"<b>Current Content:</b>\n"
        f"{safe_text_preview}\n\n"
        f"<b>Media:</b> {media_count} files\n"
        f"<b>Buttons:</b> {buttons_count} buttons\n\n"
        f"<b>Select what to edit:</b>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="Edit Text", callback_data="edit_text"),
            InlineKeyboardButton(text="Edit Media", callback_data="edit_media")
        ],
        [
            InlineKeyboardButton(text="Edit Buttons", callback_data="edit_buttons"),
            InlineKeyboardButton(text="Preview", callback_data="preview_edit")
        ],
        [
            InlineKeyboardButton(text="Save Changes", callback_data="save_changes"),
            InlineKeyboardButton(text="Cancel", callback_data="cancel_edit")
        ],
        [
            InlineKeyboardButton(text="More Options", callback_data="more_options")
        ]
    ]
    
    await message.answer(
        info_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(lambda query: query.data == "back_to_edit_menu")
async def handle_back_to_edit_menu(query: types.CallbackQuery):
    """Return to the main edit menu"""
    user_data = get_user_data(query.from_user.id)
    content = {
        "text": user_data.get("text", ""),
        "media": user_data.get("media", []),
        "buttons": user_data.get("buttons", [])
    }
    
    # We need to call show_post_content_and_edit_options but it expects a message
    # So we'll manually edit the current message
    
    text_preview = content.get("text", "")
    if len(text_preview) > 200:
        text_preview = text_preview[:197] + "..."
        
    safe_text_preview = html.escape(text_preview) if text_preview else "<i>No text content</i>"
    channel_title = html.escape(user_data.get("selected_channel", {}).get('title', 'Unknown'))
    
    media_count = len(content.get("media", []))
    buttons_count = len(content.get("buttons", []))
    
    info_text = (
        f"<b>Editing Post</b>\n\n"
        f"<b>Channel:</b> {channel_title}\n"
        f"<b>Message ID:</b> {user_data.get('edit_message_id')}\n\n"
        f"<b>Current Content:</b>\n"
        f"{safe_text_preview}\n\n"
        f"<b>Media:</b> {media_count} files\n"
        f"<b>Buttons:</b> {buttons_count} buttons\n\n"
        f"<b>Select what to edit:</b>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="Edit Text", callback_data="edit_text"),
            InlineKeyboardButton(text="Edit Media", callback_data="edit_media")
        ],
        [
            InlineKeyboardButton(text="Edit Buttons", callback_data="edit_buttons"),
            InlineKeyboardButton(text="Preview", callback_data="preview_edit")
        ],
        [
            InlineKeyboardButton(text="Save Changes", callback_data="save_changes"),
            InlineKeyboardButton(text="Cancel", callback_data="cancel_edit")
        ],
        [
            InlineKeyboardButton(text="More Options", callback_data="more_options")
        ]
    ]
    
    await query.message.edit_text(
        info_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(lambda query: query.data == "edit_text")
async def handle_edit_text(query: types.CallbackQuery):
    """Handle edit text option"""
    user_data = get_user_data(query.from_user.id)
    user_data["state"] = "editing_text"
    set_user_data(query.from_user.id, user_data)
    
    current_text = user_data.get("text", "")
    safe_text = html.escape(current_text) if current_text else "<i>No text content</i>"
    
    await query.message.edit_text(
        f"<b>Edit Text</b>\n\n"
        f"Current text:\n{safe_text}\n\n"
        "Please send the new text for the post.\n"
        "You can use HTML formatting.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Keep Current Text", callback_data="back_to_edit_menu")],
            [InlineKeyboardButton(text="Clear Text", callback_data="clear_text")]
        ])
    )
    await query.answer()

@router.callback_query(lambda query: query.data == "clear_text")
async def handle_clear_text(query: types.CallbackQuery):
    """Clear text content"""
    user_data = get_user_data(query.from_user.id)
    user_data["text"] = ""
    set_user_data(query.from_user.id, user_data)
    
    await query.answer("Text cleared")
    await handle_back_to_edit_menu(query)

@router.callback_query(lambda query: query.data == "edit_buttons")
async def handle_edit_buttons(query: types.CallbackQuery):
    """Handle edit buttons option"""
    user_data = get_user_data(query.from_user.id)
    user_data["state"] = "editing_buttons"
    set_user_data(query.from_user.id, user_data)
    
    current_buttons = user_data.get("buttons", [])
    buttons_text = ""
    for btn in current_buttons:
        buttons_text += f"• {html.escape(btn['text'])} - {html.escape(btn['url'])}\n"
    
    if not buttons_text:
        buttons_text = "<i>No buttons</i>"
    
    await query.message.edit_text(
        f"<b>Edit Buttons</b>\n\n"
        f"Current buttons:\n{buttons_text}\n\n"
        "Send new buttons in format:\n"
        "<code>Text - URL | Text 2 - URL 2</code>\n\n"
        "Example:\n"
        "<code>Visit Site - https://example.com | Join Channel - https://t.me/channel</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Keep Current Buttons", callback_data="back_to_edit_menu")],
            [InlineKeyboardButton(text="Clear Buttons", callback_data="clear_buttons")]
        ])
    )
    await query.answer()

@router.callback_query(lambda query: query.data == "clear_buttons")
async def handle_clear_buttons(query: types.CallbackQuery):
    """Clear buttons content"""
    user_data = get_user_data(query.from_user.id)
    user_data["buttons"] = []
    set_user_data(query.from_user.id, user_data)
    
    await query.answer("Buttons cleared")
    await handle_back_to_edit_menu(query)

@router.callback_query(lambda query: query.data == "edit_media")
async def handle_edit_media(query: types.CallbackQuery):
    """Handle edit media option"""
    user_data = get_user_data(query.from_user.id)
    user_data["state"] = "editing_media"
    set_user_data(query.from_user.id, user_data)
    
    current_media = user_data.get("media", [])
    media_text = f"{len(current_media)} files" if current_media else "<i>No media</i>"
    
    await query.message.edit_text(
        f"<b>Edit Media</b>\n\n"
        f"Current media: {media_text}\n\n"
        "Send new media files to replace existing media.\n"
        "Send <code>/done</code> when finished adding media.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Keep Current Media", callback_data="back_to_edit_menu")],
            [InlineKeyboardButton(text="Clear Media", callback_data="clear_media")]
        ])
    )
    await query.answer()

@router.callback_query(lambda query: query.data == "clear_media")
async def handle_clear_media(query: types.CallbackQuery):
    """Clear media content"""
    user_data = get_user_data(query.from_user.id)
    user_data["media"] = []
    set_user_data(query.from_user.id, user_data)
    
    await query.answer("Media cleared")
    await handle_back_to_edit_menu(query)

@router.callback_query(lambda query: query.data == "preview_edit")
async def handle_preview_edit(query: types.CallbackQuery):
    """Preview the edited post"""
    user_data = get_user_data(query.from_user.id)
    
    text = user_data.get("text", "")
    media = user_data.get("media", [])
    buttons = user_data.get("buttons", [])
    
    # Create inline keyboard
    keyboard = []
    if buttons:
        row = []
        for btn in buttons:
            row.append(InlineKeyboardButton(text=btn["text"], url=btn["url"]))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
    
    # Add back button
    keyboard.append([InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")])
    
    try:
        if media:
            # Send media preview
            if len(media) == 1:
                media_item = media[0]
                if media_item["type"] == "photo":
                    await query.message.answer_photo(
                        photo=media_item["file_id"],
                        caption=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                    )
                elif media_item["type"] == "video":
                    await query.message.answer_video(
                        video=media_item["file_id"],
                        caption=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                    )
                elif media_item["type"] == "document":
                    await query.message.answer_document(
                        document=media_item["file_id"],
                        caption=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                    )
                elif media_item["type"] == "animation":
                    await query.message.answer_animation(
                        animation=media_item["file_id"],
                        caption=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                    )
            else:
                # Multiple media - send as album
                # Note: Albums can't have inline keyboards, so we send text separately if needed
                # Or just show first item with caption
                await query.message.answer("Previewing media group (showing first item)...")
                media_item = media[0]
                # ... simplified for preview
                await query.message.answer_photo(
                    photo=media_item["file_id"],
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
        else:
            # Text only
            await query.message.answer(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                disable_web_page_preview=not user_data.get("link_preview", True)
            )
            
        await query.answer()
        
    except Exception as e:
        error_msg = html.escape(str(e))
        await query.message.answer(
            f"<b>Preview Failed</b>\n\nError: {error_msg}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
            ])
        )

@router.callback_query(lambda query: query.data == "save_changes")
async def handle_save_changes(query: types.CallbackQuery):
    """Save changes to the channel"""
    user_data = get_user_data(query.from_user.id)
    chat_id = user_data.get("edit_chat_id")
    message_id = user_data.get("edit_message_id")
    
    if not chat_id or not message_id:
        await query.answer("Error: Missing chat or message ID", show_alert=True)
        return
    
    await query.message.edit_text("Saving changes...")
    
    try:
        success = await update_channel_message(
            query.bot, 
            chat_id, 
            message_id, 
            user_data
        )
        
        if success:
            channel_title = html.escape(user_data.get("selected_channel", {}).get('title', 'Unknown'))
            await query.message.edit_text(
                f"<b>Success!</b>\n\n"
                f"Message in <b>{channel_title}</b> has been updated.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Edit Another Post", callback_data="back_to_channels")],
                    [InlineKeyboardButton(text="Close", callback_data="cancel_edit")]
                ])
            )
            
            # Update DB if exists
            # ...
            
            log_user_action(query.from_user.id, "EDIT_POST", f"Chat: {chat_id}, Msg: {message_id}")
            
        else:
            await query.message.edit_text(
                "<b>Update Failed</b>\n\n"
                "Could not update the message. Please check bot permissions.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Try Again", callback_data="save_changes")],
                    [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )
            
    except Exception as e:
        error_msg = html.escape(str(e))
        await query.message.edit_text(
            f"<b>Error</b>\n\n{error_msg}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
            ])
        )
        logger.error(f"Save changes error: {e}")

def create_inline_buttons_keyboard(buttons):
    """Helper to create inline keyboard from buttons list"""
    if not buttons:
        return None
        
    keyboard = []
    row = []
    for btn in buttons:
        row.append(InlineKeyboardButton(text=btn["text"], url=btn["url"]))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Pin message
@router.callback_query(lambda query: query.data == "pin_message")
async def handle_pin_message(query: types.CallbackQuery):
    """Pin the selected message"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    chat_id = user_data.get("edit_chat_id")
    message_id = user_data.get("edit_message_id")
    selected_channel = user_data.get("selected_channel", {})
    channel_name = html.escape(selected_channel.get("title", selected_channel.get("username", "Unknown")))
    
    if not chat_id or not message_id:
        await query.message.edit_text(
            "<b>Error</b>\n\nNo message selected for pinning.",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        await query.message.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=False
        )
        
        await query.message.edit_text(
            f"<b>Message Pinned Successfully!</b>\n\n"
            f"The message has been pinned in <b>{channel_name}</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Unpin Message", callback_data="unpin_message")],
                [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
            ])
        )
        
    except Exception as e:
        error_msg = str(e)
        if "CHAT_ADMIN_REQUIRED" in error_msg:
            await query.message.edit_text(
                f"<b>Pin Failed - Admin Rights Required</b>\n\n"
                f"The bot needs admin rights in <b>{channel_name}</b> to pin messages.\n\n"
                f"<b>Please make sure:</b>\n"
                f"• Bot is an admin in the channel\n"
                f"• Bot has 'Pin Messages' permission",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )
        else:
            safe_error = html.escape(error_msg)
            await query.message.edit_text(
                f"<b>Pin Failed</b>\n\n"
                f"Could not pin the message.\n\n"
                f"<b>Error:</b> {safe_error}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )

# Unpin message
@router.callback_query(lambda query: query.data == "unpin_message")
async def handle_unpin_message(query: types.CallbackQuery):
    """Unpin the selected message"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    chat_id = user_data.get("edit_chat_id")
    message_id = user_data.get("edit_message_id")
    selected_channel = user_data.get("selected_channel", {})
    channel_name = html.escape(selected_channel.get("title", selected_channel.get("username", "Unknown")))
    
    if not chat_id or not message_id:
        await query.message.edit_text(
            "<b>Error</b>\n\nNo message selected for unpinning.",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        await query.message.bot.unpin_chat_message(
            chat_id=chat_id,
            message_id=message_id
        )
        
        await query.message.edit_text(
            f"<b>Message Unpinned Successfully!</b>\n\n"
            f"The message has been unpinned from <b>{channel_name}</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")],
                [InlineKeyboardButton(text="Close", callback_data="cancel_edit")]
            ])
        )
        
    except Exception as e:
        error_msg = str(e)
        if "CHAT_ADMIN_REQUIRED" in error_msg:
            await query.message.edit_text(
                f"<b>Unpin Failed - Admin Rights Required</b>\n\n"
                f"The bot needs admin rights in <b>{channel_name}</b> to unpin messages.\n\n"
                f"<b>Please make sure:</b>\n"
                f"• Bot is an admin in the channel\n"
                f"• Bot has 'Pin Messages' permission",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )
        else:
            safe_error = html.escape(error_msg)
            await query.message.edit_text(
                f"<b>Unpin Failed</b>\n\n"
                f"Could not unpin the message.\n\n"
                f"<b>Error:</b> {safe_error}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )


# Delete message
@router.callback_query(lambda query: query.data == "delete_message")
async def handle_delete_message(query: types.CallbackQuery):
    """Delete the selected message with confirmation"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    selected_channel = user_data.get("selected_channel", {})
    channel_name = html.escape(selected_channel.get("title", selected_channel.get("username", "Unknown")))
    
    await query.message.edit_text(
        f"<b>DELETE MESSAGE CONFIRMATION</b>\n\n"
        f"<b>Warning:</b> This action cannot be undone!\n\n"
        f"Are you sure you want to <b>permanently delete</b> this message from <b>{channel_name}</b>?\n\n"
        f"The message will be completely removed and cannot be recovered.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Yes, Delete", callback_data="confirm_delete_message"),
                InlineKeyboardButton(text="Cancel", callback_data="back_to_edit_menu")
            ]
        ])
    )


# Confirm delete message
@router.callback_query(lambda query: query.data == "confirm_delete_message")
async def handle_confirm_delete_message(query: types.CallbackQuery):
    """Confirm and delete the message"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    chat_id = user_data.get("edit_chat_id")
    message_id = user_data.get("edit_message_id")
    selected_channel = user_data.get("selected_channel", {})
    channel_name = html.escape(selected_channel.get("title", selected_channel.get("username", "Unknown")))
    
    if not chat_id or not message_id:
        await query.message.edit_text(
            "<b>Error</b>\n\nNo message selected for deletion.",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        await query.message.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )
        
        await query.message.edit_text(
            f"<b>Message Deleted Successfully!</b>\n\n"
            f"The message has been permanently deleted from <b>{channel_name}</b>.\n\n"
            f"This action has been completed and cannot be undone.",
            parse_mode=ParseMode.HTML
        )
        
        # Clear user data since message is deleted
        clear_user_data(query.from_user.id)
        
    except Exception as e:
        error_msg = str(e)
        if "CHAT_ADMIN_REQUIRED" in error_msg:
            await query.message.edit_text(
                f"<b>Delete Failed - Admin Rights Required</b>\n\n"
                f"The bot needs admin rights in <b>{channel_name}</b> to delete messages.\n\n"
                f"<b>Please make sure:</b>\n"
                f"• Bot is an admin in the channel\n"
                f"• Bot has 'Delete Messages' permission",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )
        elif "MESSAGE_DELETE_FORBIDDEN" in error_msg:
            await query.message.edit_text(
                f"<b>Delete Failed - Permission Denied</b>\n\n"
                f"Cannot delete this message. This usually happens when:\n\n"
                f"• Message is too old (48+ hours)\n"
                f"• You don't have permission to delete this message\n"
                f"• The message was posted by someone else",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )
        else:
            safe_error = html.escape(error_msg)
            await query.message.edit_text(
                f"<b>Delete Failed</b>\n\n"
                f"Could not delete the message.\n\n"
                f"<b>Error:</b> {safe_error}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )


# More options
@router.callback_query(lambda query: query.data == "more_options")
async def handle_more_options(query: types.CallbackQuery):
    """Show more advanced options for the message"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    selected_channel = user_data.get("selected_channel", {})
    channel_name = html.escape(selected_channel.get("title", selected_channel.get("username", "Unknown")))
    
    await query.message.edit_text(
        f"<b>MORE OPTIONS - {channel_name}</b>\n\n"
        f"<b>Advanced message management:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Copy Message", callback_data="copy_message"),
                InlineKeyboardButton(text="Get Message Link", callback_data="get_message_link")
            ],
            [
                InlineKeyboardButton(text="Message Stats", callback_data="message_stats"),
                InlineKeyboardButton(text="Clone Message", callback_data="clone_message")
            ],
            [
                InlineKeyboardButton(text="Forward Message", callback_data="forward_message"),
                InlineKeyboardButton(text="Quote Message", callback_data="quote_message")
            ],
            [
                InlineKeyboardButton(text="Schedule Edit", callback_data="schedule_edit"),
                InlineKeyboardButton(text="Notification Settings", callback_data="notification_settings")
            ],
            [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
        ])
    )


# Copy message
@router.callback_query(lambda query: query.data == "copy_message")
async def handle_copy_message(query: types.CallbackQuery):
    """Copy message content to clipboard (show content for copying)"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    original_content = user_data.get("original_content", {})
    
    text_content = original_content.get("text", "")
    media_info = ""
    buttons_info = ""
    
    if original_content.get("media"):
        media_count = len(original_content["media"])
        media_types = [m["type"] for m in original_content["media"]]
        media_info = f"\n\n<b>Media:</b> {media_count} file(s) ({', '.join(set(media_types))})"
    
    if original_content.get("buttons"):
        buttons_info = f"\n\n<b>Buttons:</b>\n"
        for btn in original_content["buttons"]:
            buttons_info += f"• {html.escape(btn['text'])} → {html.escape(btn['url'])}\n"
    
    copy_content = f"<b>MESSAGE CONTENT TO COPY:</b>\n\n"
    
    if text_content:
        safe_text = html.escape(text_content)
        copy_content += f"<b>Text:</b>\n<pre>{safe_text}</pre>"
    else:
        copy_content += "<b>Text:</b> <i>No text content</i>"
    
    copy_content += media_info + buttons_info
    
    await query.message.edit_text(
        copy_content,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to More Options", callback_data="more_options")]
        ])
    )


# Get message link
@router.callback_query(lambda query: query.data == "get_message_link")
async def handle_get_message_link(query: types.CallbackQuery):
    """Generate and show the message link"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    chat_id = user_data.get("edit_chat_id")
    message_id = user_data.get("edit_message_id")
    selected_channel = user_data.get("selected_channel", {})
    channel_title = html.escape(selected_channel.get("title", "Unknown"))
    
    if not chat_id or not message_id:
        await query.message.edit_text(
            "<b>Error</b>\n\nNo message selected.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Generate message link
    message_link = ""
    
    if chat_id.startswith("@"):
        # Public channel
        username = chat_id[1:]  # Remove @ symbol
        message_link = f"https://t.me/{username}/{message_id}"
    elif chat_id.startswith("-100"):
        # Private channel
        chat_id_numeric = chat_id[4:]  # Remove -100 prefix
        message_link = f"https://t.me/c/{chat_id_numeric}/{message_id}"
    
    await query.message.edit_text(
        f"<b>MESSAGE LINK</b>\n\n"
        f"<b>Channel:</b> {channel_title}\n"
        f"<b>Message ID:</b> {message_id}\n\n"
        f"<b>Link:</b>\n<code>{message_link}</code>\n\n"
        f"<b>Tip:</b> Tap the link to copy it to your clipboard.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to More Options", callback_data="more_options")]
        ])
    )


# Message stats
@router.callback_query(lambda query: query.data == "message_stats")
async def handle_message_stats(query: types.CallbackQuery):
    """Show message statistics (basic info)"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    original_content = user_data.get("original_content", {})
    selected_channel = user_data.get("selected_channel", {})
    channel_title = html.escape(selected_channel.get("title", "Unknown"))
    
    text_length = len(original_content.get("text", ""))
    media_count = len(original_content.get("media", []))
    button_count = len(original_content.get("buttons", []))
    
    stats_text = (
        f"<b>MESSAGE STATISTICS</b>\n\n"
        f"<b>Channel:</b> {channel_title}\n"
        f"<b>Message ID:</b> {user_data.get('edit_message_id', 'Unknown')}\n\n"
        f"<b>Content Analysis:</b>\n"
        f"•  Text length: {text_length} characters\n"
        f"•  Media files: {media_count}\n"
        f"•  Buttons: {button_count}\n\n"
    )
    
    if original_content.get("media"):
        media_types = [m["type"] for m in original_content["media"]]
        unique_types = list(set(media_types))
        stats_text += f"<b>Media types:</b> {', '.join(unique_types)}\n"
    
    await query.message.edit_text(
        stats_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to More Options", callback_data="more_options")]
        ])
    )


# Placeholder handlers for advanced features
@router.callback_query(lambda query: query.data in ["clone_message", "forward_message", "quote_message", "schedule_edit", "notification_settings"])
async def handle_advanced_features(query: types.CallbackQuery):
    """Handle advanced features (to be implemented)"""
    await query.answer()
    
    feature_names = {
        "clone_message": "Clone Message",
        "forward_message": "Forward Message", 
        "quote_message": "Quote Message",
        "schedule_edit": "Schedule Edit",
        "notification_settings": "Notification Settings"
    }
    
    feature_name = feature_names.get(query.data, "Feature")
    
    await query.message.edit_text(
        f"<b>{feature_name}</b>\n\n"
        f"This feature is coming soon!\n\n"
        f"Stay tuned for updates.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to More Options", callback_data="more_options")]
        ])
    )


# Quick action handlers for posts without buttons
@router.callback_query(lambda query: query.data == "quick_add_button")
async def handle_quick_add_button(query: types.CallbackQuery):
    """Quick add button action for posts without buttons"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    user_data["state"] = "editing_buttons"
    set_user_data(query.from_user.id, user_data)
    
    await query.message.edit_text(
        f"<b>Quick Add Button</b>\n\n"
        f"<b>No buttons currently in this post</b>\n\n"
        f"<b>Send buttons in format:</b>\n"
        f"<code>Text1 - URL1 | Text2 - URL2</code>\n\n"
        f"<b>Example:</b>\n"
        f"<code>Visit Website - https://example.com | Join Channel - https://t.me/channel</code>\n\n"
        f"<b>Tip:</b> Adding buttons makes your post more interactive!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
        ])
    )


@router.callback_query(lambda query: query.data == "quick_add_media")
async def handle_quick_add_media(query: types.CallbackQuery):
    """Quick add media action for posts without buttons"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    current_media = user_data.get("media", [])
    user_data["state"] = "editing_media"
    set_user_data(query.from_user.id, user_data)
    
    media_info = f"<b>Current media:</b> {len(current_media)} file(s)" if current_media else "<b>No media currently</b>"
    
    await query.message.edit_text(
        f"<b>Quick Add Media</b>\n\n"
        f"{media_info}\n\n"
        f"<b>Send new media files (photos, videos, documents):</b>\n"
        f"You can send multiple files. Send /done when finished.\n\n"
        f"<b>Tip:</b> Media makes your posts more engaging and visual!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Remove All Media", callback_data="remove_all_media")],
            [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
        ])
    )


@router.callback_query(lambda query: query.data == "quick_add_text")
async def handle_quick_add_text(query: types.CallbackQuery):
    """Quick add text action for posts without buttons and text"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    user_data["state"] = "editing_text"
    set_user_data(query.from_user.id, user_data)
    
    await query.message.edit_text(
        f"<b>Quick Add Text</b>\n\n"
        f"<b>No text currently in this post</b>\n\n"
        f"<b>Send the text content for your post:</b>\n\n"
        f"<b>Tip:</b> You can use HTML formatting:\n"
        f"• <code>&lt;b&gt;bold&lt;/b&gt;</code> for <b>bold text</b>\n"
        f"• <code>&lt;i&gt;italic&lt;/i&gt;</code> for <i>italic text</i>\n"
        f"• <code>&lt;code&gt;code&lt;/code&gt;</code> for <code>code text</code>\n"
        f"• <code>&lt;a href='url'&gt;link text&lt;/a&gt;</code> for links",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Back to Edit Menu", callback_data="back_to_edit_menu")]
        ])
    )


@router.callback_query(lambda query: query.data == "separator")
async def handle_separator_click(query: types.CallbackQuery):
    """Handle separator line click (do nothing, just provide feedback)"""
    await query.answer("This is just a visual separator", show_alert=False)


# Message handlers for edit states
@router.message(lambda message: 
    get_user_data(message.from_user.id).get("state") == "editing_text" and
    message.text and
    message.text not in ["Back to Edit Menu"]
)
async def process_edit_text_input(message: types.Message):
    """Process text input during edit mode"""
    user_data = get_user_data(message.from_user.id)
    user_data["text"] = message.text
    user_data["state"] = "editing_post"
    set_user_data(message.from_user.id, user_data)
    
    safe_text = html.escape(message.text)
    preview = safe_text[:100] + "..." if len(safe_text) > 100 else safe_text
    
    await message.answer(
        f"<b>Text Updated!</b>\n\n"
        f"Preview: {preview}",
        parse_mode=ParseMode.HTML
    )
    
    # Go back to edit menu
    selected_channel = user_data.get("selected_channel", {})
    await show_post_content_and_edit_options(message, {
        "text": user_data.get("text", ""),
        "media": user_data.get("media", []),
        "buttons": user_data.get("buttons", [])
    }, selected_channel)


@router.message(lambda message: 
    get_user_data(message.from_user.id).get("state") == "editing_media" and
    (message.photo or message.video or message.document or message.animation)
)
async def process_edit_media_input(message: types.Message):
    """Process media input during edit mode"""
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
    elif message.animation:
        media_item = {
            "type": "animation",
            "file_id": message.animation.file_id,
            "caption": message.caption or ""
        }
    
    if media_item:
        user_data["media"].append(media_item)
        set_user_data(message.from_user.id, user_data)
        media_count = len(user_data["media"])
        
        await message.answer(
            f"<b>Media Added!</b>\n\n"
            f"Total media files: {media_count}\n"
            f"You can send more media or use the buttons below to continue.",
            parse_mode=ParseMode.HTML
        )


@router.message(lambda message: 
    get_user_data(message.from_user.id).get("state") == "editing_buttons" and
    message.text and
    message.text not in ["Back to Edit Menu"]
)
async def process_edit_buttons_input(message: types.Message):
    """Process buttons input during edit mode"""
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
                import re
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
                    safe_url = html.escape(url)
                    await message.answer(
                        f"<b>Invalid URL format for button:</b> {safe_text}\n"
                        f"URL: {safe_url}\n\n"
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
            # Replace all buttons with new ones for edit mode
            user_data["buttons"] = parsed_buttons
            user_data["state"] = "editing_post"
            set_user_data(message.from_user.id, user_data)
            
            buttons_summary = "\n".join([f"• {html.escape(btn['text'])} → {html.escape(btn['url'])}" for btn in parsed_buttons])
            
            await message.answer(
                f"<b>{len(parsed_buttons)} Button(s) Updated!</b>\n\n"
                f"Updated buttons:\n{buttons_summary}",
                parse_mode=ParseMode.HTML
            )
            
            # Go back to edit menu
            selected_channel = user_data.get("selected_channel", {})
            await show_post_content_and_edit_options(message, {
                "text": user_data.get("text", ""),
                "media": user_data.get("media", []),
                "buttons": user_data.get("buttons", [])
            }, selected_channel)
        else:
            await message.answer(
                "<b>No valid buttons found</b>\n\n"
                "Please check the format and try again.",
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        error_msg = html.escape(str(e))
        await message.answer(
            f"<b>Error parsing buttons</b>\n\n"
            f"Error: {error_msg}\n\n"
            f"Please use the correct format:\n"
            f"<code>Button1 - URL1 | Button2 - URL2</code>",
            parse_mode=ParseMode.HTML
        )


@router.message(lambda message: 
    get_user_data(message.from_user.id).get("state") == "editing_media" and
    message.text == "/done"
)
async def handle_done_editing_media(message: types.Message):
    """Handle done command for media editing"""
    user_data = get_user_data(message.from_user.id)
    user_data["state"] = "editing_post"
    set_user_data(message.from_user.id, user_data)
    
    media_count = len(user_data.get("media", []))
    await message.answer(
        f"<b>Media editing completed!</b>\n\n"
        f"Total media files: {media_count}",
        parse_mode=ParseMode.HTML
    )
    
    # Go back to edit menu
    selected_channel = user_data.get("selected_channel", {})
    await show_post_content_and_edit_options(message, {
        "text": user_data.get("text", ""),
        "media": user_data.get("media", []),
        "buttons": user_data.get("buttons", [])
    }, selected_channel)


async def update_channel_message(bot, chat_id: str, message_id: int, user_data: dict) -> bool:
    """
    Update an existing message in a channel with new content
    
    Args:
        bot: The bot instance
        chat_id: Channel chat ID (can be username or numeric ID)
        message_id: Message ID to edit
        user_data: User data containing the updated content
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        # Validate user_data has content
        has_text = user_data.get("text") and user_data["text"].strip()
        has_media = user_data.get("media") and len(user_data["media"]) > 0
        
        if not has_text and not has_media:
            logger.error("No content to update - both text and media are empty")
            return False
        
        # Create inline keyboard for buttons if any
        inline_keyboard = create_inline_buttons_keyboard(user_data.get("buttons", []))
        
        # Handle different content types
        if has_media and len(user_data["media"]) == 1:
            # Single media file - edit media message
            media_item = user_data["media"][0]
            caption_text = user_data.get("text", "")
            
            if media_item["type"] == "photo":
                media = InputMediaPhoto(
                    media=media_item["file_id"],
                    caption=caption_text,
                    parse_mode=ParseMode.HTML
                )
            elif media_item["type"] == "video":
                media = InputMediaVideo(
                    media=media_item["file_id"],
                    caption=caption_text,
                    parse_mode=ParseMode.HTML
                )
            elif media_item["type"] == "document":
                media = InputMediaDocument(
                    media=media_item["file_id"],
                    caption=caption_text,
                    parse_mode=ParseMode.HTML
                )
            elif media_item["type"] == "animation":
                media = InputMediaAnimation(
                    media=media_item["file_id"],
                    caption=caption_text,
                    parse_mode=ParseMode.HTML
                )
            else:
                logger.error(f"Unsupported media type: {media_item['type']}")
                return False
            
            # Edit media message
            await bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=inline_keyboard
            )
            
        elif has_media and len(user_data["media"]) > 1:
            # Multiple media files - cannot edit media group directly
            # This is a limitation of Telegram API - media groups can't be edited
            # We can only edit the caption of the first message in the group
            text_content = user_data.get("text", "")
            
            try:
                # Try to edit as if it's the first message of a media group
                await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=text_content,
                    parse_mode=ParseMode.HTML,
                    reply_markup=inline_keyboard
                )
            except Exception as media_group_error:
                logger.warning(f"Could not edit media group caption: {media_group_error}")
                # Try to edit as text message instead
                if text_content:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=text_content,
                        parse_mode=ParseMode.HTML,
                        reply_markup=inline_keyboard,
                        disable_web_page_preview=not user_data.get("link_preview", True)
                    )
                else:
                    logger.error("Cannot edit media group without text content")
                    return False
                    
        else:
            # Text only message
            if not has_text:
                logger.error("No text content to update")
                return False
                
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=user_data["text"],
                parse_mode=ParseMode.HTML,
                reply_markup=inline_keyboard,
                disable_web_page_preview=not user_data.get("link_preview", True)
            )
        
        logger.info(f"Successfully updated message {message_id} in chat {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating channel message: {e}")
        return False
