"""
Post preview and publishing functionality
"""
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.types import InputMediaPhoto, InputMediaVideo

from constants import router
from db import db
from utils.data_store import get_user_data, clear_user_data
from utils.keyboards import create_inline_buttons_keyboard

@router.message(lambda message: message.text == "Preview Post")
async def cmd_preview_post(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    if not user_data:
        from .post_creation import cmd_create_post
        await cmd_create_post(message)
        return
    
    # Check if there's any content to preview
    if not user_data.get("text") and not user_data.get("media"):
        await message.answer(
            " **No Content to Preview**\n\n"
            "Please add some text or media before previewing your post.",
            parse_mode=ParseMode.MARKDOWN
        )
        from .post_menu import show_post_menu
        await show_post_menu(message)
        return
    
    # Create preview
    preview_text = "**POST PREVIEW**\n\n"
    
    if user_data.get("text"):
        preview_text += f"**Text:**\n{user_data['text']}\n\n"
    
    if user_data.get("media"):
        preview_text += f"**Media:** {len(user_data['media'])} file(s) attached\n\n"
    
    if user_data.get("buttons"):
        preview_text += "**Buttons:**\n"
        for button in user_data["buttons"]:
            preview_text += f" {button['text']} → {button['url']}\n"
        preview_text += "\n"
    
    preview_text += "**Settings:**\n"
    preview_text += f" Pin Post: {'Yes' if user_data.get('pin_post', False) else 'No'}\n"
    preview_text += f" Notifications: {'On' if user_data.get('notifications', True) else 'Off'}\n"
    preview_text += f" Link Preview: {'On' if user_data.get('link_preview', True) else 'Off'}\n"
    
    # Create inline keyboard for buttons if any
    inline_keyboard = create_inline_buttons_keyboard(user_data.get("buttons", []))
    
    try:
        # Send preview
        if user_data.get("media") and len(user_data["media"]) == 1:
            # Single media file
            media_item = user_data["media"][0]
            if media_item["type"] == "photo":
                await message.answer_photo(
                    photo=media_item["file_id"],
                    caption=preview_text,
                    reply_markup=inline_keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif media_item["type"] == "video":
                await message.answer_video(
                    video=media_item["file_id"],
                    caption=preview_text,
                    reply_markup=inline_keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif media_item["type"] == "document":
                await message.answer_document(
                    document=media_item["file_id"],
                    caption=preview_text,
                    reply_markup=inline_keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
        elif user_data.get("media") and len(user_data["media"]) > 1:
            # Multiple media files - send as media group
            media_group = []
            for i, media_item in enumerate(user_data["media"][:10]):  # Telegram limit is 10
                if media_item["type"] == "photo":
                    media_group.append(InputMediaPhoto(
                        media=media_item["file_id"],
                        caption=preview_text if i == 0 else None,
                        parse_mode=ParseMode.MARKDOWN if i == 0 else None
                    ))
                elif media_item["type"] == "video":
                    media_group.append(InputMediaVideo(
                        media=media_item["file_id"],
                        caption=preview_text if i == 0 else None,
                        parse_mode=ParseMode.MARKDOWN if i == 0 else None
                    ))
            
            await message.answer_media_group(media=media_group)
            
            if inline_keyboard:
                await message.answer("Buttons:", reply_markup=inline_keyboard)
        else:
            # Text only
            await message.answer(
                preview_text,
                reply_markup=inline_keyboard,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=not user_data.get("link_preview", True)
            )
        
        # Return to main post menu
        from .post_menu import show_post_menu
        await show_post_menu(message)
        
    except Exception as e:
        await message.answer(
            f"**Preview Error**\n\n"
            f"Failed to show preview: {str(e)}\n\n"
            "Please try again or check your media files.",
            parse_mode=ParseMode.MARKDOWN
        )
        from .post_menu import show_post_menu
        await show_post_menu(message)

@router.message(lambda message: message.text == "Publish Post")
async def cmd_publish_post(message: types.Message):
    # Get user data and validate it exists
    user_data = get_user_data(message.from_user.id)
    
    # Debug logging - you can remove this later
    print(f"DEBUG: User {message.from_user.id} publish attempt")
    print(f"DEBUG: User data exists: {user_data is not None}")
    if user_data:
        print(f"DEBUG: Has text: {bool(user_data.get('text'))}")
        print(f"DEBUG: Has media: {bool(user_data.get('media'))}")
        print(f"DEBUG: Text content: '{user_data.get('text', '')}'")
        print(f"DEBUG: Media count: {len(user_data.get('media', []))}")
    
    if not user_data:
        await message.answer(
            "**No Post Data Found**\n\n"
            "Please create a post first using the menu options.",
            parse_mode=ParseMode.MARKDOWN
        )
        from .post_creation import cmd_create_post
        await cmd_create_post(message)
        return
      # Check if there's any content to publish
    has_text = bool(user_data.get("text") and user_data["text"].strip())
    has_media = bool(user_data.get("media") and len(user_data["media"]) > 0)
    
    # Additional debug logging
    print(f"DEBUG: has_text evaluation: {has_text}")
    print(f"DEBUG: has_media evaluation: {has_media}")
    print(f"DEBUG: text value: '{user_data.get('text', 'NONE')}'")
    print(f"DEBUG: text stripped: '{user_data.get('text', '').strip()}'")
    print(f"DEBUG: media value: {user_data.get('media', 'NONE')}")
    
    if not has_text and not has_media:
        media_count = len(user_data.get('media', []))
        await message.answer(
            "**No Content to Publish**\n\n"
            "Please add some text or media before publishing your post.\n\n"
            "Current status:\n"
            f"• Text: {'Empty' if not has_text else 'Present'}\n"
            f"• Media: {'None' if not has_media else f'{media_count} files'}\n\n"
            f"Debug info:\n"
            f"• Raw text: '{user_data.get('text', 'NONE')}'\n"
            f"• Raw media: {user_data.get('media', 'NONE')}",
            parse_mode=ParseMode.MARKDOWN
        )
        from .post_menu import show_post_menu
        await show_post_menu(message)
        return
    
    # Get connected channels
    try:
        user_info = await db.users.find_one({"user_id": message.from_user.id})
        connected_channels = user_info.get("connected_channels", []) if user_info else []
        
        if not connected_channels:
            await message.answer(
                "**No Connected Channels**\n\n"
                "You need to connect to at least one channel first.\n"
                "Use `/connect @channelname` to connect to a channel.",
                parse_mode=ParseMode.MARKDOWN
            )
            from .post_menu import show_post_menu
            await show_post_menu(message)
            return
        
        # Show channel selection interface
        from .channel_selection import show_channel_selection
        await show_channel_selection(message, action="publish")
        
    except Exception as e:
        await message.answer(
            f"**Database Error**\n\n"
            f"Failed to retrieve channel information: {str(e)}\n\n"
            "Please try again later.",
            parse_mode=ParseMode.MARKDOWN
        )
        from .post_menu import show_post_menu
        await show_post_menu(message)
  
async def publish_post_to_channel(message: types.Message, channel_data: dict, user_data: dict):
    """Publish a post to a specific channel"""
    try:
        connected_chat = channel_data.get("username") or channel_data.get("chat_id")
        
        if not connected_chat:
            raise Exception("Invalid channel data - no username or chat_id found")
        
        # Validate user_data has content
        has_text = user_data.get("text") and user_data["text"].strip()
        has_media = user_data.get("media") and len(user_data["media"]) > 0
        
        if not has_text and not has_media:
            raise Exception("No content to publish - both text and media are empty")
        
        # Create inline keyboard for buttons if any
        inline_keyboard = create_inline_buttons_keyboard(user_data.get("buttons", []))
        
        sent_message = None
        
        # Send the post
        if has_media and len(user_data["media"]) == 1:
            # Single media file
            media_item = user_data["media"][0]
            caption_text = user_data.get("text", "")
            
            if media_item["type"] == "photo":
                sent_message = await message.bot.send_photo(
                    chat_id=connected_chat,
                    photo=media_item["file_id"],
                    caption=caption_text,
                    reply_markup=inline_keyboard,
                    parse_mode=ParseMode.HTML,
                    disable_notification=not user_data.get("notifications", True)
                )
            elif media_item["type"] == "video":
                sent_message = await message.bot.send_video(
                    chat_id=connected_chat,
                    video=media_item["file_id"],
                    caption=caption_text,
                    reply_markup=inline_keyboard,
                    parse_mode=ParseMode.HTML,
                    disable_notification=not user_data.get("notifications", True)
                )
            elif media_item["type"] == "document":
                sent_message = await message.bot.send_document(
                    chat_id=connected_chat,
                    document=media_item["file_id"],
                    caption=caption_text,
                    reply_markup=inline_keyboard,
                    parse_mode=ParseMode.HTML,
                    disable_notification=not user_data.get("notifications", True)
                )
                
        elif has_media and len(user_data["media"]) > 1:
            # Multiple media files - send as media group
            media_group = []
            text_content = user_data.get("text", "")
            
            for i, media_item in enumerate(user_data["media"][:10]):  # Telegram limit is 10
                if media_item["type"] == "photo":
                    media_group.append(InputMediaPhoto(
                        media=media_item["file_id"],
                        caption=text_content if i == 0 else None,
                        parse_mode=ParseMode.HTML if i == 0 and text_content else None
                    ))
                elif media_item["type"] == "video":
                    media_group.append(InputMediaVideo(
                        media=media_item["file_id"],
                        caption=text_content if i == 0 else None,
                        parse_mode=ParseMode.HTML if i == 0 and text_content else None
                    ))
            
            sent_messages = await message.bot.send_media_group(
                chat_id=connected_chat,
                media=media_group,
                disable_notification=not user_data.get("notifications", True)
            )
            sent_message = sent_messages[0] if sent_messages else None
            
            if inline_keyboard:
                await message.bot.send_message(
                    chat_id=connected_chat,
                    text="*Action buttons for the post above*",
                    reply_markup=inline_keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_notification=not user_data.get("notifications", True)
                )
        else:
            # Text only
            if not has_text:
                raise Exception("No text content to publish")
                
            sent_message = await message.bot.send_message(
                chat_id=connected_chat,
                text=user_data["text"],
                reply_markup=inline_keyboard,
                parse_mode=ParseMode.HTML,
                disable_notification=not user_data.get("notifications", True),
                disable_web_page_preview=not user_data.get("link_preview", True)
            )
        
        # Pin the message if requested
        if user_data.get("pin_post", False) and sent_message:
            try:
                await message.bot.pin_chat_message(
                    chat_id=connected_chat,
                    message_id=sent_message.message_id,
                    disable_notification=not user_data.get("notifications", True)
                )
            except Exception as pin_error:
                # Don't raise exception for pin failures, just log it
                print(f"Failed to pin message: {pin_error}")
        
        return sent_message
        
    except Exception as e:
        print(f"Error in publish_post_to_channel: {e}")
        raise e