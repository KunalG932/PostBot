"""
Edit post functionality - allows users to edit existing posts by first selecting channel then providing message links
"""
import re
import logging
from aiogram import types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAnimation

from constants import router
from db import db
from utils.data_store import get_user_data, set_user_data, clear_user_data
from utils.keyboards import create_inline_buttons_keyboard

# Set up logging
logger = logging.getLogger(__name__)


@router.message(Command("edit"))
async def cmd_edit_post(message: types.Message):
    """Start edit post process - show channel selection"""
    user_data = get_user_data(message.from_user.id)
    
    # Get user's connected channels
    user_info = await db.users.find_one({"user_id": message.from_user.id})
    
    if not user_info or not user_info.get("connected_channels"):
        await message.reply(
            " **No Connected Channels**\n\n"
            "You don't have any connected channels yet.\n"
            "Use `/connect` to connect your channels first.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    connected_channels = user_info.get("connected_channels", [])
    
    if len(connected_channels) == 1:
        # If user has only one channel, select it automatically
        channel = connected_channels[0]
        user_data["selected_channel"] = channel
        user_data["state"] = "waiting_edit_link"
        set_user_data(message.from_user.id, user_data)
        
        await show_post_link_request(message, channel)
    else:
        # Show channel selection if user has multiple channels
        user_data["state"] = "selecting_edit_channel"
        set_user_data(message.from_user.id, user_data)
        
        await show_channel_selection(message, connected_channels)


async def show_channel_selection(message: types.Message, channels: list, is_callback: bool = False):
    """Show channel selection for editing"""
    keyboard = []
    
    for i, channel in enumerate(channels):
        channel_name = channel.get("title", channel.get("username", "Unknown Channel"))
        keyboard.append([
            InlineKeyboardButton(
                text=f" {channel_name}",
                callback_data=f"select_edit_channel_{i}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text=" Cancel", callback_data="cancel_edit")])
    
    content = (
        " **Edit Post**\n\n"
        " **Select the channel where you want to edit a post:**"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    if is_callback:
        await message.edit_text(
            content,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup
        )
    else:
        await message.reply(
            content,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup
        )


@router.callback_query(lambda query: query.data.startswith("select_edit_channel_"))
async def handle_channel_selection(query: types.CallbackQuery):
    """Handle channel selection for editing"""
    await query.answer()
    
    try:
        channel_index = int(query.data.split("_")[-1])
        
        # Get user's connected channels
        user_info = await db.users.find_one({"user_id": query.from_user.id})
        connected_channels = user_info.get("connected_channels", [])
        
        if channel_index >= len(connected_channels):
            await query.message.edit_text(
                " **Error**\n\nInvalid channel selection.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        selected_channel = connected_channels[channel_index]
        
        # Store selected channel in user data
        user_data = get_user_data(query.from_user.id)
        user_data["selected_channel"] = selected_channel
        user_data["state"] = "waiting_edit_link"
        set_user_data(query.from_user.id, user_data)
        
        await show_post_link_request(query.message, selected_channel, is_callback=True)
        
    except (ValueError, IndexError):
        await query.message.edit_text(
            " **Error**\n\nInvalid channel selection.",
            parse_mode=ParseMode.MARKDOWN
        )


async def show_post_link_request(message: types.Message, channel: dict, is_callback: bool = False):
    """Show post link request for selected channel"""
    channel_name = channel.get("title", channel.get("username", "Unknown Channel"))
    
    content = (
        f" **Edit Post in {channel_name}**\n\n"
        f" **Send me the message link of the post you want to edit:**\n\n"
        f"**Message link formats:**\n"
        f"• `https://t.me/channelname/123`\n"
        f"• `https://t.me/c/1234567890/123`\n\n"
        f"**How to get the message link:**\n"
        f"1.  Open the post in your channel\n"
        f"2.  Click the three dots (...) or long press\n"
        f"3.  Select 'Copy Link'\n"
        f"4.  Send the link here"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Back to Channel Selection", callback_data="back_to_channel_selection")],
        [InlineKeyboardButton(text=" Cancel", callback_data="cancel_edit")]
    ])
    
    if is_callback:
        await message.edit_text(
            content,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup
        )
    else:
        await message.reply(
            content,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=markup
        )


@router.callback_query(lambda query: query.data == "back_to_channel_selection")
async def handle_back_to_channel_selection(query: types.CallbackQuery):
    """Go back to channel selection"""
    await query.answer()
    
    # Get user's connected channels
    user_info = await db.users.find_one({"user_id": query.from_user.id})
    connected_channels = user_info.get("connected_channels", [])
    
    user_data = get_user_data(query.from_user.id)
    user_data["state"] = "selecting_edit_channel"
    set_user_data(query.from_user.id, user_data)
    
    await show_channel_selection(query.message, connected_channels, is_callback=True)


@router.message(lambda message: message.text and message.text.startswith("https://t.me/"))
async def handle_message_link(message: types.Message):
    """Handle message links for editing"""
    user_data = get_user_data(message.from_user.id)
    
    if user_data.get("state") != "waiting_edit_link":
        return  # Not in edit mode
    
    selected_channel = user_data.get("selected_channel")
    if not selected_channel:
        await message.reply(
            " **Error**\n\nNo channel selected. Please start over with `/edit`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    message_link = message.text.strip()
    
    # Log user and channel information
    logger.info(f"User {message.from_user.id} (@{message.from_user.username}) sent message link: {message_link}")
    logger.info(f"Selected channel info: {selected_channel}")
    
    # Parse the message link
    chat_id, message_id = await parse_message_link(message_link)
    
    if not chat_id or not message_id:
        logger.warning(f"Failed to parse message link: {message_link}")
        await message.reply(
            " **Invalid Message Link**\n\n"
            "Please send a valid Telegram message link.\n\n"
            "**Valid formats:**\n"
            "`https://t.me/channelname/123`\n"
            "`https://t.me/c/1234567890/123`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    logger.info(f"Parsed link - Chat ID: {chat_id}, Message ID: {message_id}")
    
    # Verify the link belongs to the selected channel
    channel_match = await verify_channel_match(chat_id, selected_channel)
    logger.info(f"Channel match result: {channel_match}")
    
    if not channel_match:
        channel_name = selected_channel.get("title", selected_channel.get("username", "Unknown"))
        logger.warning(f"Channel mismatch - Link chat_id: {chat_id}, Channel: {selected_channel}")
        await message.reply(
            f" **Channel Mismatch**\n\n"
            f"This message link doesn't belong to the selected channel **{channel_name}**.\n\n"
            f"Please send a message link from the correct channel.\n\n"
            f"**Debug Info:**\n"
            f"Link Chat ID: `{chat_id}`\n"
            f"Channel Chat ID: `{selected_channel.get('chat_id', 'N/A')}`\n"
            f"Channel Username: `{selected_channel.get('username', 'N/A')}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Try to get the message content
    try:
        post_content = await get_message_content(message.bot, chat_id, message_id, message.from_user.id)
        
        if not post_content:
            await message.reply(
                " **Message Not Found**\n\n"
                "Could not find the message. Please check:\n"
                "• The message exists\n"
                "• The link is correct\n"
                "• Bot has access to the channel",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Store the original message info for editing
        user_data["edit_chat_id"] = chat_id
        user_data["edit_message_id"] = message_id
        user_data["original_content"] = post_content
        
        # Load the content into current post data
        user_data["text"] = post_content.get("text", "")
        user_data["media"] = post_content.get("media", [])
        user_data["buttons"] = post_content.get("buttons", [])
        user_data["state"] = "editing_post"
        
        set_user_data(message.from_user.id, user_data)
        
        # Show the post content and edit options
        await show_post_content_and_edit_options(message, post_content, selected_channel)
        
    except Exception as e:
        await message.reply(
            f" **Error Loading Post**\n\n"
            f"Error: {str(e)}\n\n"
            "Please make sure:\n"
            "• The message exists\n"
            "• Bot has admin access to the channel\n"
            "• The link is correct",
            parse_mode=ParseMode.MARKDOWN
        )


async def verify_channel_match(message_chat_id: str, selected_channel: dict) -> bool:
    """Verify that the message link belongs to the selected channel"""
    logger.info(f"Verifying channel match:")
    logger.info(f"  Message Chat ID: {message_chat_id}")
    logger.info(f"  Selected Channel: {selected_channel}")
    
    channel_chat_id = str(selected_channel.get("chat_id", ""))
    channel_username = selected_channel.get("username", "")
    
    logger.info(f"  Channel Chat ID: {channel_chat_id}")
    logger.info(f"  Channel Username: {channel_username}")
    
    # Direct chat_id match
    if channel_chat_id == message_chat_id:
        logger.info(f"   Direct chat_id match: {channel_chat_id} == {message_chat_id}")
        return True
    
    # Username match (for public channels)
    if channel_username == message_chat_id:
        logger.info(f"   Username match: {channel_username} == {message_chat_id}")
        return True
        
    # Username without @ symbol
    if message_chat_id.startswith("@") and channel_username == message_chat_id[1:]:
        logger.info(f"   Username match (without @): {channel_username} == {message_chat_id[1:]}")
        return True
        
    # Chat ID with @ prefix
    if message_chat_id.startswith("@") and channel_chat_id == message_chat_id[1:]:
        logger.info(f"   Chat ID match (with @): {channel_chat_id} == {message_chat_id[1:]}")
        return True
    
    logger.warning(f"   No match found between message_chat_id '{message_chat_id}' and channel (chat_id: '{channel_chat_id}', username: '{channel_username}')")
    return False


async def show_post_content_and_edit_options(message: types.Message, content: dict, channel: dict):
    """Show the current post content and edit options"""
    channel_name = channel.get("title", channel.get("username", "Unknown Channel"))
    
    # Build content display
    content_text = f" **EDITING POST FROM {channel_name.upper()}**\n\n"
    content_text += " **CURRENT POST CONTENT:**\n\n"
    
    # Show text content
    if content.get("text"):
        preview_text = content["text"]
        if len(preview_text) > 300:
            preview_text = preview_text[:300] + "..."
        content_text += f"** Text:**\n{preview_text}\n\n"
    else:
        content_text += "** Text:** _No text content_\n\n"
    
    # Show media info
    if content.get("media"):
        media_count = len(content["media"])
        media_types = [m["type"] for m in content["media"]]
        content_text += f"** Media:** {media_count} file(s)\n"
        content_text += f"**Types:** {', '.join(set(media_types))}\n\n"
    else:
        content_text += "** Media:** _No media files_\n\n"
    
    # Show buttons info
    if content.get("buttons"):
        button_count = len(content["buttons"])
        content_text += f"** Buttons:** {button_count} button(s)\n"
        for i, btn in enumerate(content["buttons"][:3]):  # Show first 3 buttons
            content_text += f"  {i+1}. {btn['text']}\n"
        if len(content["buttons"]) > 3:
            content_text += f"  ... and {len(content['buttons']) - 3} more\n"
        content_text += "\n"
    else:
        content_text += "** Buttons:** _No buttons_\n\n"
    
    content_text += "** What would you like to edit?**"
    
    # Create edit options keyboard
    keyboard = []
    
    # Edit options
    if content.get("text"):
        keyboard.append([InlineKeyboardButton(text=" Edit Text", callback_data="edit_text")])
    else:
        keyboard.append([InlineKeyboardButton(text=" Add Text", callback_data="edit_text")])
    
    keyboard.append([InlineKeyboardButton(text=" Edit Media", callback_data="edit_media")])
    keyboard.append([InlineKeyboardButton(text=" Edit Buttons", callback_data="edit_buttons")])
    
    # Special section for posts without buttons - add quick action buttons
    if not content.get("buttons"):
        content_text += "\n\n **This post has no buttons. Quick actions:**"
        keyboard.append([
            InlineKeyboardButton(text=" Add Button", callback_data="quick_add_button"),
            InlineKeyboardButton(text=" Add Media", callback_data="quick_add_media")
        ])
        if not content.get("text"):
            keyboard.append([InlineKeyboardButton(text=" Add Text", callback_data="quick_add_text")])
    
    # Separator line if quick actions were added
    if not content.get("buttons"):
        keyboard.append([InlineKeyboardButton(text="", callback_data="separator")])
    
    # Message actions
    keyboard.append([
        InlineKeyboardButton(text=" Pin Message", callback_data="pin_message"),
        InlineKeyboardButton(text=" Unpin Message", callback_data="unpin_message")
    ])
    
    keyboard.append([
        InlineKeyboardButton(text=" Delete Message", callback_data="delete_message"),
        InlineKeyboardButton(text=" More Options", callback_data="more_options")
    ])
    
    # Action buttons
    keyboard.append([
        InlineKeyboardButton(text=" Save Changes", callback_data="save_edit")
    ])
    
    keyboard.append([InlineKeyboardButton(text=" Cancel Edit", callback_data="cancel_edit")])
    
    await message.reply(
        content_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


async def parse_message_link(link: str) -> tuple:
    """Parse message link to extract chat_id and message_id"""
    logger.info(f"Parsing message link: {link}")
    
    # Pattern for private channels: https://t.me/c/1234567890/123 (check this first)
    private_pattern = r"^https://t\.me/c/(\d+)/(\d+)$"
    
    # Pattern for public channels: https://t.me/channelname/123 (check this second)
    public_pattern = r"^https://t\.me/([^/c][^/]*)/(\d+)$"
    
    # Try private pattern first
    private_match = re.match(private_pattern, link)
    if private_match:
        chat_id = f"-100{private_match.group(1)}"  # Add -100 prefix for supergroups/channels
        message_id = int(private_match.group(2))
        logger.info(f"Parsed as private channel - Chat ID: {chat_id}, Message ID: {message_id}")
        return chat_id, message_id
    
    # Try public pattern second
    public_match = re.match(public_pattern, link)
    if public_match:
        channel_username = public_match.group(1)
        message_id = int(public_match.group(2))
        result_chat_id = f"@{channel_username}"
        logger.info(f"Parsed as public channel - Username: {channel_username}, Message ID: {message_id}, Result Chat ID: {result_chat_id}")
        return result_chat_id, message_id
    
    logger.warning(f"Failed to parse message link: {link}")
    return None, None


async def get_message_content(bot, chat_id: str, message_id: int, user_id: int) -> dict:
    """Get message content from Telegram"""
    try:
        # Get the original message
        original_message = await bot.forward_message(
            chat_id=user_id,  # Forward to user's private chat temporarily
            from_chat_id=chat_id,
            message_id=message_id
        )
        
        # Extract content from the forwarded message
        content = {
            "text": "",
            "media": [],
            "buttons": []
        }
        
        # Extract text
        if original_message.text:
            content["text"] = original_message.text
        elif original_message.caption:
            content["text"] = original_message.caption
        
        # Extract media
        if original_message.photo:
            content["media"].append({
                "type": "photo",
                "file_id": original_message.photo[-1].file_id,
                "caption": original_message.caption or ""
            })
        elif original_message.video:
            content["media"].append({
                "type": "video",
                "file_id": original_message.video.file_id,
                "caption": original_message.caption or ""
            })
        elif original_message.document:
            content["media"].append({
                "type": "document",
                "file_id": original_message.document.file_id,
                "caption": original_message.caption or ""
            })
        elif original_message.animation:
            content["media"].append({
                "type": "animation",
                "file_id": original_message.animation.file_id,
                "caption": original_message.caption or ""
            })
        
        # Extract buttons from reply markup
        if original_message.reply_markup and hasattr(original_message.reply_markup, 'inline_keyboard'):
            for row in original_message.reply_markup.inline_keyboard:
                for button in row:
                    if button.url:  # Only URL buttons
                        content["buttons"].append({
                            "text": button.text,
                            "url": button.url
                        })
        
        # Delete the forwarded message
        try:
            await bot.delete_message(chat_id=user_id, message_id=original_message.message_id)
        except:
            pass  # Ignore if deletion fails
        
        return content
        
    except Exception as e:
        print(f"Error getting message content: {e}")
        
        # Fallback: return template for manual entry
        return {
            "text": " **Content Extraction Failed**\n\nPlease manually update the content using the edit options below.\n\n **Tip:** Copy your original message content and paste it when editing.",
            "media": [],
            "buttons": []
        }


# Edit text callback
@router.callback_query(lambda query: query.data == "edit_text")
async def handle_edit_text(query: types.CallbackQuery):
    """Handle edit text action"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    current_text = user_data.get("text", "")
    
    user_data["state"] = "editing_text"
    set_user_data(query.from_user.id, user_data)
    
    if current_text:
        preview = f"**Current text:**\n{current_text[:500]}{'...' if len(current_text) > 500 else ''}"
    else:
        preview = "**No text currently**"
    
    await query.message.edit_text(
        f" **Edit Text Content**\n\n"
        f"{preview}\n\n"
        f" **Send the new text content:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
        ])
    )


# Edit media callback
@router.callback_query(lambda query: query.data == "edit_media")
async def handle_edit_media(query: types.CallbackQuery):
    """Handle edit media action"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    current_media = user_data.get("media", [])
    
    user_data["state"] = "editing_media"
    set_user_data(query.from_user.id, user_data)
    
    media_info = f"**Current media:** {len(current_media)} file(s)" if current_media else "**No media currently**"
    
    await query.message.edit_text(
        f" **Edit Media Content**\n\n"
        f"{media_info}\n\n"
        f" **Send new media files (photos, videos, documents):**\n"
        f"You can send multiple files. Send /done when finished.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Remove All Media", callback_data="remove_all_media")],
            [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
        ])
    )


# Edit buttons callback
@router.callback_query(lambda query: query.data == "edit_buttons")
async def handle_edit_buttons(query: types.CallbackQuery):
    """Handle edit buttons action"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    current_buttons = user_data.get("buttons", [])
    
    user_data["state"] = "editing_buttons"
    set_user_data(query.from_user.id, user_data)
    
    buttons_info = ""
    if current_buttons:
        buttons_info = f"**Current buttons:**\n"
        for i, btn in enumerate(current_buttons, 1):
            buttons_info += f"{i}. {btn['text']} → {btn['url']}\n"
    else:
        buttons_info = "**No buttons currently**"
    
    await query.message.edit_text(
        f" **Edit Buttons**\n\n"
        f"{buttons_info}\n\n"
        f"**Send buttons in format:**\n"
        f"`Text1 - URL1 | Text2 - URL2`\n\n"
        f"**Example:**\n"
        f"`Visit Website - https://example.com | Join Channel - https://t.me/channel`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Remove All Buttons", callback_data="remove_all_buttons")],
            [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
        ])
    )


# Back to edit menu
@router.callback_query(lambda query: query.data == "back_to_edit_menu")
async def handle_back_to_edit_menu(query: types.CallbackQuery):
    """Go back to edit menu"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    selected_channel = user_data.get("selected_channel", {})
    
    user_data["state"] = "editing_post"
    set_user_data(query.from_user.id, user_data)
    
    await show_post_content_and_edit_options(query.message, {
        "text": user_data.get("text", ""),
        "media": user_data.get("media", []),
        "buttons": user_data.get("buttons", [])
    }, selected_channel)


# Preview changes
@router.callback_query(lambda query: query.data == "preview_edit")
async def handle_preview_edit(query: types.CallbackQuery):
    """Preview the edited post"""
    await query.answer()
    
    from .preview_publish import show_post_preview
    user_data = get_user_data(query.from_user.id)
    
    # Temporarily change state to preview
    original_state = user_data.get("state")
    user_data["state"] = "preview"
    set_user_data(query.from_user.id, user_data)
    
    await show_post_preview(query.message, is_edit_preview=True)
    
    # Restore original state
    user_data["state"] = original_state
    set_user_data(query.from_user.id, user_data)


# Save changes
@router.callback_query(lambda query: query.data == "save_edit")
async def handle_save_edit(query: types.CallbackQuery):
    """Save the edited post"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    
    chat_id = user_data.get("edit_chat_id")
    message_id = user_data.get("edit_message_id")
    selected_channel = user_data.get("selected_channel", {})
    channel_name = selected_channel.get("title", selected_channel.get("username", "Unknown"))
    
    if not chat_id or not message_id:
        await query.message.edit_text(
            " **Error**\n\nEdit session expired. Please start over.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        # Update the message
        success = await update_channel_message(query.message.bot, chat_id, message_id, user_data)
        
        if success:
            await query.message.edit_text(
                f" **Post Updated Successfully!**\n\n"
                f"Your changes have been saved to **{channel_name}**.\n\n"
                f" **Updated Message:** [View Post]({user_data.get('message_link', '#')})",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Clear edit data
            clear_user_data(query.from_user.id)
        else:
            await query.message.edit_text(
                " **Update Failed**\n\n"
                "Could not update the post. Please check:\n"
                "• Bot has admin rights in the channel\n"
                "• The message still exists\n"
                "• You have permission to edit",
                parse_mode=ParseMode.MARKDOWN
            )
    
    except Exception as e:
        await query.message.edit_text(
            f" **Update Error**\n\n"
            f"Error: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )


# Cancel edit
@router.callback_query(lambda query: query.data == "cancel_edit")
async def handle_cancel_edit(query: types.CallbackQuery):
    """Cancel the edit process"""
    await query.answer()
    
    clear_user_data(query.from_user.id)
    
    await query.message.edit_text(
        " **Edit Cancelled**\n\n"
        "No changes were made to your post.",
        parse_mode=ParseMode.MARKDOWN
    )


# Remove all media
@router.callback_query(lambda query: query.data == "remove_all_media")
async def handle_remove_all_media(query: types.CallbackQuery):
    """Remove all media from post"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    user_data["media"] = []
    set_user_data(query.from_user.id, user_data)
    
    await query.answer(" All media removed", show_alert=True)
    await handle_back_to_edit_menu(query)


# Remove all buttons
@router.callback_query(lambda query: query.data == "remove_all_buttons")
async def handle_remove_all_buttons(query: types.CallbackQuery):
    """Remove all buttons from post"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    user_data["buttons"] = []
    set_user_data(query.from_user.id, user_data)
    
    await query.answer(" All buttons removed", show_alert=True)
    await handle_back_to_edit_menu(query)


# Pin message
@router.callback_query(lambda query: query.data == "pin_message")
async def handle_pin_message(query: types.CallbackQuery):
    """Pin the selected message"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    chat_id = user_data.get("edit_chat_id")
    message_id = user_data.get("edit_message_id")
    selected_channel = user_data.get("selected_channel", {})
    channel_name = selected_channel.get("title", selected_channel.get("username", "Unknown"))
    
    if not chat_id or not message_id:
        await query.message.edit_text(
            " **Error**\n\nNo message selected for pinning.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        await query.message.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=False
        )
        
        await query.message.edit_text(
            f" **Message Pinned Successfully!**\n\n"
            f"The message has been pinned in **{channel_name}**.\n\n"
            f" All channel subscribers will receive a notification about the pinned message.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")],
                [InlineKeyboardButton(text=" Close", callback_data="cancel_edit")]
            ])
        )
        
    except Exception as e:
        error_msg = str(e)
        if "CHAT_ADMIN_REQUIRED" in error_msg:
            await query.message.edit_text(
                f" **Pin Failed - Admin Rights Required**\n\n"
                f"The bot needs admin rights in **{channel_name}** to pin messages.\n\n"
                f"**Please make sure:**\n"
                f"• Bot is an admin in the channel\n"
                f"• Bot has 'Pin Messages' permission",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )
        else:
            await query.message.edit_text(
                f" **Pin Failed**\n\n"
                f"Could not pin the message.\n\n"
                f"**Error:** {error_msg}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
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
    channel_name = selected_channel.get("title", selected_channel.get("username", "Unknown"))
    
    if not chat_id or not message_id:
        await query.message.edit_text(
            " **Error**\n\nNo message selected for unpinning.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        await query.message.bot.unpin_chat_message(
            chat_id=chat_id,
            message_id=message_id
        )
        
        await query.message.edit_text(
            f" **Message Unpinned Successfully!**\n\n"
            f"The message has been unpinned from **{channel_name}**.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")],
                [InlineKeyboardButton(text=" Close", callback_data="cancel_edit")]
            ])
        )
        
    except Exception as e:
        error_msg = str(e)
        if "CHAT_ADMIN_REQUIRED" in error_msg:
            await query.message.edit_text(
                f" **Unpin Failed - Admin Rights Required**\n\n"
                f"The bot needs admin rights in **{channel_name}** to unpin messages.\n\n"
                f"**Please make sure:**\n"
                f"• Bot is an admin in the channel\n"
                f"• Bot has 'Pin Messages' permission",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )
        else:
            await query.message.edit_text(
                f" **Unpin Failed**\n\n"
                f"Could not unpin the message.\n\n"
                f"**Error:** {error_msg}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )


# Delete message
@router.callback_query(lambda query: query.data == "delete_message")
async def handle_delete_message(query: types.CallbackQuery):
    """Delete the selected message with confirmation"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    selected_channel = user_data.get("selected_channel", {})
    channel_name = selected_channel.get("title", selected_channel.get("username", "Unknown"))
    
    await query.message.edit_text(
        f" **DELETE MESSAGE CONFIRMATION**\n\n"
        f" **Warning:** This action cannot be undone!\n\n"
        f"Are you sure you want to **permanently delete** this message from **{channel_name}**?\n\n"
        f"The message will be completely removed and cannot be recovered.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=" Yes, Delete", callback_data="confirm_delete_message"),
                InlineKeyboardButton(text=" Cancel", callback_data="back_to_edit_menu")
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
    channel_name = selected_channel.get("title", selected_channel.get("username", "Unknown"))
    
    if not chat_id or not message_id:
        await query.message.edit_text(
            " **Error**\n\nNo message selected for deletion.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        await query.message.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )
        
        await query.message.edit_text(
            f" **Message Deleted Successfully!**\n\n"
            f"The message has been permanently deleted from **{channel_name}**.\n\n"
            f" This action has been completed and cannot be undone.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Clear user data since message is deleted
        clear_user_data(query.from_user.id)
        
    except Exception as e:
        error_msg = str(e)
        if "CHAT_ADMIN_REQUIRED" in error_msg:
            await query.message.edit_text(
                f" **Delete Failed - Admin Rights Required**\n\n"
                f"The bot needs admin rights in **{channel_name}** to delete messages.\n\n"
                f"**Please make sure:**\n"
                f"• Bot is an admin in the channel\n"
                f"• Bot has 'Delete Messages' permission",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )
        elif "MESSAGE_DELETE_FORBIDDEN" in error_msg:
            await query.message.edit_text(
                f" **Delete Failed - Permission Denied**\n\n"
                f"Cannot delete this message. This usually happens when:\n\n"
                f"• Message is too old (48+ hours)\n"
                f"• You don't have permission to delete this message\n"
                f"• The message was posted by someone else",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )
        else:
            await query.message.edit_text(
                f" **Delete Failed**\n\n"
                f"Could not delete the message.\n\n"
                f"**Error:** {error_msg}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
                ])
            )


# More options
@router.callback_query(lambda query: query.data == "more_options")
async def handle_more_options(query: types.CallbackQuery):
    """Show more advanced options for the message"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    selected_channel = user_data.get("selected_channel", {})
    channel_name = selected_channel.get("title", selected_channel.get("username", "Unknown"))
    
    await query.message.edit_text(
        f" **MORE OPTIONS - {channel_name}**\n\n"
        f" **Advanced message management:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=" Copy Message", callback_data="copy_message"),
                InlineKeyboardButton(text=" Get Message Link", callback_data="get_message_link")
            ],
            [
                InlineKeyboardButton(text=" Message Stats", callback_data="message_stats"),
                InlineKeyboardButton(text=" Clone Message", callback_data="clone_message")
            ],
            [
                InlineKeyboardButton(text=" Forward Message", callback_data="forward_message"),
                InlineKeyboardButton(text=" Quote Message", callback_data="quote_message")
            ],
            [
                InlineKeyboardButton(text=" Schedule Edit", callback_data="schedule_edit"),
                InlineKeyboardButton(text=" Notification Settings", callback_data="notification_settings")
            ],
            [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
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
        media_info = f"\n\n **Media:** {media_count} file(s) ({', '.join(set(media_types))})"
    
    if original_content.get("buttons"):
        buttons_info = f"\n\n **Buttons:**\n"
        for btn in original_content["buttons"]:
            buttons_info += f"• {btn['text']} → {btn['url']}\n"
    
    copy_content = f" **MESSAGE CONTENT TO COPY:**\n\n"
    
    if text_content:
        copy_content += f"**Text:**\n```\n{text_content}\n```"
    else:
        copy_content += "**Text:** _No text content_"
    
    copy_content += media_info + buttons_info
    
    await query.message.edit_text(
        copy_content,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Back to More Options", callback_data="more_options")]
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
    
    if not chat_id or not message_id:
        await query.message.edit_text(
            " **Error**\n\nNo message selected.",
            parse_mode=ParseMode.MARKDOWN
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
        f" **MESSAGE LINK**\n\n"
        f"**Channel:** {selected_channel.get('title', 'Unknown')}\n"
        f"**Message ID:** {message_id}\n\n"
        f"**Link:**\n`{message_link}`\n\n"
        f" **Tip:** Tap the link to copy it to your clipboard.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Back to More Options", callback_data="more_options")]
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
    
    text_length = len(original_content.get("text", ""))
    media_count = len(original_content.get("media", []))
    button_count = len(original_content.get("buttons", []))
    
    stats_text = (
        f" **MESSAGE STATISTICS**\n\n"
        f"**Channel:** {selected_channel.get('title', 'Unknown')}\n"
        f"**Message ID:** {user_data.get('edit_message_id', 'Unknown')}\n\n"
        f"**Content Analysis:**\n"
        f"•  Text length: {text_length} characters\n"
        f"•  Media files: {media_count}\n"
        f"•  Buttons: {button_count}\n\n"
    )
    
    if original_content.get("media"):
        media_types = [m["type"] for m in original_content["media"]]
        unique_types = list(set(media_types))
        stats_text += f"**Media types:** {', '.join(unique_types)}\n"
    
    await query.message.edit_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Back to More Options", callback_data="more_options")]
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
        f" **{feature_name}**\n\n"
        f"This feature is coming soon!\n\n"
        f"Stay tuned for updates. ",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Back to More Options", callback_data="more_options")]
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
        f" **Quick Add Button**\n\n"
        f"**No buttons currently in this post**\n\n"
        f"**Send buttons in format:**\n"
        f"`Text1 - URL1 | Text2 - URL2`\n\n"
        f"**Example:**\n"
        f"`Visit Website - https://example.com | Join Channel - https://t.me/channel`\n\n"
        f" **Tip:** Adding buttons makes your post more interactive!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
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
    
    media_info = f"**Current media:** {len(current_media)} file(s)" if current_media else "**No media currently**"
    
    await query.message.edit_text(
        f" **Quick Add Media**\n\n"
        f"{media_info}\n\n"
        f" **Send new media files (photos, videos, documents):**\n"
        f"You can send multiple files. Send /done when finished.\n\n"
        f" **Tip:** Media makes your posts more engaging and visual!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Remove All Media", callback_data="remove_all_media")],
            [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
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
        f" **Quick Add Text**\n\n"
        f"**No text currently in this post**\n\n"
        f" **Send the text content for your post:**\n\n"
        f" **Tip:** You can use HTML formatting:\n"
        f"• `<b>bold</b>` for **bold text**\n"
        f"• `<i>italic</i>` for *italic text*\n"
        f"• `<code>code</code>` for `code text`\n"
        f"• `<a href='url'>link text</a>` for links",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Back to Edit Menu", callback_data="back_to_edit_menu")]
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
    message.text not in [" Back to Edit Menu"]
)
async def process_edit_text_input(message: types.Message):
    """Process text input during edit mode"""
    user_data = get_user_data(message.from_user.id)
    user_data["text"] = message.text
    user_data["state"] = "editing_post"
    set_user_data(message.from_user.id, user_data)
    
    await message.answer(
        f" **Text Updated!**\n\n"
        f"Preview: {message.text[:100]}{'...' if len(message.text) > 100 else ''}",
        parse_mode=ParseMode.MARKDOWN
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
            f" **Media Added!**\n\n"
            f"Total media files: {media_count}\n"
            f"You can send more media or use the buttons below to continue.",
            parse_mode=ParseMode.MARKDOWN
        )


@router.message(lambda message: 
    get_user_data(message.from_user.id).get("state") == "editing_buttons" and
    message.text and
    message.text not in [" Back to Edit Menu"]
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
                    await message.answer(
                        f" **Invalid URL format for button:** {button_text}\n"
                        f"URL: {url}\n\n"
                        f"Please check the format and try again.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
            else:
                await message.answer(
                    f" **Invalid format for:** {pair}\n\n"
                    f"Use format: Button Text - URL\n"
                    f"Example: Visit Site - https://example.com",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        if parsed_buttons:
            # Replace all buttons with new ones for edit mode
            user_data["buttons"] = parsed_buttons
            user_data["state"] = "editing_post"
            set_user_data(message.from_user.id, user_data)
            
            buttons_summary = "\n".join([f"• {btn['text']} → {btn['url']}" for btn in parsed_buttons])
            
            await message.answer(
                f" **{len(parsed_buttons)} Button(s) Updated!**\n\n"
                f"Updated buttons:\n{buttons_summary}",
                parse_mode=ParseMode.MARKDOWN
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
                " **No valid buttons found**\n\n"
                "Please check the format and try again.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    except Exception as e:
        await message.answer(
            f" **Error parsing buttons**\n\n"
            f"Error: {str(e)}\n\n"
            f"Please use the correct format:\n"
            f"`Button1 - URL1 | Button2 - URL2`",
            parse_mode=ParseMode.MARKDOWN
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
        f" **Media editing completed!**\n\n"
        f"Total media files: {media_count}",
        parse_mode=ParseMode.MARKDOWN
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