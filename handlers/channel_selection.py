"""
Channel selection functionality for multi-channel posting
"""
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from constants import router
from db import db
from utils.data_store import get_user_data, set_user_data


async def show_channel_selection(message: types.Message, action="publish"):
    """Show channel selection interface"""
    user_info = await db.users.find_one({"user_id": message.from_user.id})
    connected_channels = user_info.get("connected_channels", []) if user_info else []
    
    if not connected_channels:
        await message.answer(
            " **No Connected Channels**\n\n"
            "You need to connect to at least one channel first.\n"
            "Use `/connect @channelname` to connect to a channel.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if len(connected_channels) == 1:
        # If only one channel, auto-select it
        if action == "publish":
            await publish_to_channels(message, [0])
        return
    
    # Create keyboard for channel selection
    keyboard = []
    
    # Individual channel buttons
    for i, channel in enumerate(connected_channels):
        title = channel.get("title", channel.get("username", "Unknown"))
        keyboard.append([
            InlineKeyboardButton(
                text=f" {title}",
                callback_data=f"select_channel_{i}"
            )
        ])
    
    # Multi-select options
    keyboard.append([
        InlineKeyboardButton(
            text="Select Multiple",
            callback_data="multi_select_start"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="All Channels",
            callback_data="select_all_channels"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="Cancel",
            callback_data="cancel_channel_selection"
        )
    ])
    
    response = " **Select Channels to Post**\n\n"
    response += "Choose one or more channels to publish your post:\n\n"
    
    for i, channel in enumerate(connected_channels, 1):
        title = channel.get("title", channel.get("username", "Unknown"))
        username = channel.get("username", "")
        response += f"{i}. **{title}**\n"
        if username:
            response += f"    {username}\n"
    
    await message.answer(
        response,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(lambda query: query.data.startswith("select_channel_"))
async def handle_single_channel_select(query: types.CallbackQuery):
    """Handle single channel selection"""
    await query.answer()
    
    try:
        channel_index = int(query.data.split("_")[-1])
        await publish_to_channels(query.message, [channel_index], user_id=query.from_user.id)
    except (ValueError, IndexError):
        try:
            await query.message.edit_text(
                " **Error**\n\nInvalid channel selection.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            await query.message.answer(
                " **Error**\n\nInvalid channel selection.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        # Handle any other errors during publishing
        try:
            await query.message.edit_text(
                f" **Publishing Error**\n\n{str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            await query.message.answer(
                f" **Publishing Error**\n\n{str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )


@router.callback_query(lambda query: query.data == "select_all_channels")
async def handle_all_channels_select(query: types.CallbackQuery):
    """Handle all channels selection"""
    await query.answer()
    
    try:
        user_info = await db.users.find_one({"user_id": query.from_user.id})
        connected_channels = user_info.get("connected_channels", []) if user_info else []
        
        if not connected_channels:
            try:
                await query.message.edit_text(
                    " **No Connected Channels**",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                await query.message.answer(
                    " **No Connected Channels**",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # Select all channels
        channel_indices = list(range(len(connected_channels)))
        await publish_to_channels(query.message, channel_indices, user_id=query.from_user.id)
    
    except Exception as e:
        # Handle any errors during the process
        try:
            await query.message.edit_text(
                f" **Error**\n\n{str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            await query.message.answer(
                f" **Error**\n\n{str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )


@router.callback_query(lambda query: query.data == "multi_select_start")
async def handle_multi_select_start(query: types.CallbackQuery):
    """Start multi-select mode"""
    await query.answer()
    
    user_info = await db.users.find_one({"user_id": query.from_user.id})
    connected_channels = user_info.get("connected_channels", []) if user_info else []
    
    if not connected_channels:
        await query.message.edit_text(
            " **No Connected Channels**",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Initialize selection state
    user_data = get_user_data(query.from_user.id)
    user_data["selected_channels"] = []
    set_user_data(query.from_user.id, user_data)
    
    await show_multi_select_interface(query.message, connected_channels, [])


async def show_multi_select_interface(message: types.Message, channels, selected_indices):
    """Show multi-select interface"""
    keyboard = []
    
    # Channel selection buttons
    for i, channel in enumerate(channels):
        title = channel.get("title", channel.get("username", "Unknown"))
        is_selected = i in selected_indices
        emoji = "" if is_selected else ""
        keyboard.append([
            InlineKeyboardButton(
                text=f"{emoji} {title}",
                callback_data=f"toggle_channel_{i}"
            )
        ])
    
    # Action buttons
    action_row = []
    if selected_indices:
        action_row.append(
            InlineKeyboardButton(
                text=f" Post to {len(selected_indices)} channel(s)",
                callback_data="confirm_multi_select"
            )
        )
    
    action_row.append(
        InlineKeyboardButton(
            text="Cancel",
            callback_data="cancel_channel_selection"
        )
    )
    
    keyboard.append(action_row)
    
    response = " **Multi-Channel Selection**\n\n"
    response += "Select the channels you want to post to:\n\n"
    
    for i, channel in enumerate(channels):
        title = channel.get("title", channel.get("username", "Unknown"))
        username = channel.get("username", "")
        is_selected = i in selected_indices
        emoji = "" if is_selected else ""
        response += f"{emoji} **{title}**\n"
        if username:
            response += f"    {username}\n"
    
    if selected_indices:
        response += f"\n**Selected:** {len(selected_indices)} channel(s)"
    
    await message.edit_text(
        response,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(lambda query: query.data.startswith("toggle_channel_"))
async def handle_toggle_channel(query: types.CallbackQuery):
    """Handle toggling channel selection in multi-select mode"""
    await query.answer()
    
    try:
        channel_index = int(query.data.split("_")[-1])
        
        user_data = get_user_data(query.from_user.id)
        selected_channels = user_data.get("selected_channels", [])
        
        if channel_index in selected_channels:
            selected_channels.remove(channel_index)
        else:
            selected_channels.append(channel_index)
        
        user_data["selected_channels"] = selected_channels
        set_user_data(query.from_user.id, user_data)
        
        # Get channels to refresh interface
        user_info = await db.users.find_one({"user_id": query.from_user.id})
        connected_channels = user_info.get("connected_channels", []) if user_info else []
        
        await show_multi_select_interface(query.message, connected_channels, selected_channels)
        
    except (ValueError, IndexError):
        await query.answer(" Error selecting channel", show_alert=True)


@router.callback_query(lambda query: query.data == "confirm_multi_select")
async def handle_confirm_multi_select(query: types.CallbackQuery):
    """Confirm multi-select and publish"""
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    selected_channels = user_data.get("selected_channels", [])
    
    if not selected_channels:
        await query.answer(" No channels selected", show_alert=True)
        return
    
    await publish_to_channels(query.message, selected_channels, user_id=query.from_user.id)


@router.callback_query(lambda query: query.data == "cancel_channel_selection")
async def handle_cancel_selection(query: types.CallbackQuery):
    """Cancel channel selection"""
    await query.answer()
    
    await query.message.edit_text(
        " **Cancelled**\n\nChannel selection cancelled.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Return to post menu
    from .post_menu import show_post_menu
    await show_post_menu(query.message)


async def publish_to_channels(message: types.Message, channel_indices, user_id=None):
    """Publish post to selected channels"""
    from .preview_publish import publish_post_to_channel
    
    # Use provided user_id or fall back to message.from_user.id
    actual_user_id = user_id if user_id is not None else message.from_user.id
    
    user_info = await db.users.find_one({"user_id": actual_user_id})
    connected_channels = user_info.get("connected_channels", []) if user_info else []
    
    user_data = get_user_data(actual_user_id)
    
    # Debug logging
    print(f"DEBUG CHANNEL_SELECTION: User {actual_user_id} publish_to_channels")
    print(f"DEBUG CHANNEL_SELECTION: User data exists: {user_data is not None}")
    if user_data:
        print(f"DEBUG CHANNEL_SELECTION: Has text: {bool(user_data.get('text'))}")
        print(f"DEBUG CHANNEL_SELECTION: Has media: {bool(user_data.get('media'))}")
        print(f"DEBUG CHANNEL_SELECTION: Text content: '{user_data.get('text', '')}'")
        print(f"DEBUG CHANNEL_SELECTION: Media count: {len(user_data.get('media', []))}")
        print(f"DEBUG CHANNEL_SELECTION: Full user_data keys: {list(user_data.keys())}")
    else:
        print(f"DEBUG CHANNEL_SELECTION: user_data is None!")
    
    if not user_data:
        await message.edit_text(
            " **No Content to Publish**\n\n"
            "Please create a post first.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Validate channel indices
    valid_indices = [i for i in channel_indices if 0 <= i < len(connected_channels)]
    
    if not valid_indices:
        await message.edit_text(
            " **Invalid Channel Selection**",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    selected_channels = [connected_channels[i] for i in valid_indices]
    
    # Show publishing status
    if len(selected_channels) == 1:
        channel_name = selected_channels[0].get("title", selected_channels[0].get("username", "Unknown"))
        status_text = f" **Publishing to: {channel_name}**\n\nYour post is being sent..."
    else:
        status_text = f" **Publishing to {len(selected_channels)} channels**\n\nYour post is being sent..."
    
    # Try to edit the message, if that fails, send a new message
    try:
        await message.edit_text(status_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as edit_error:
        # If editing fails, send a new message
        await message.answer(status_text, parse_mode=ParseMode.MARKDOWN)
        # Update message reference for result display
        message = await message.answer("Processing...")
        await message.delete()
    
    # Publish to each selected channel
    success_count = 0
    failed_channels = []
    
    for channel in selected_channels:
        try:
            await publish_post_to_channel(message, channel, user_data)
            success_count += 1
        except Exception as e:
            failed_channels.append({
                "channel": channel,
                "error": str(e)
            })
    
    # Show results
    if success_count == len(selected_channels):
        # All successful
        if len(selected_channels) == 1:
            result_text = " **Post Published Successfully!**\n\n"
            result_text += f"Your post has been sent to **{selected_channels[0].get('title', 'the channel')}**"
        else:
            result_text = f" **Post Published Successfully!**\n\n"
            result_text += f"Your post has been sent to **{len(selected_channels)}** channels"
    elif success_count > 0:
        # Partial success
        result_text = f" **Partially Published**\n\n"
        result_text += f"Successfully posted to **{success_count}** out of **{len(selected_channels)}** channels\n\n"
        result_text += "**Failed channels:**\n"
        for failed in failed_channels:
            channel_name = failed["channel"].get("title", failed["channel"].get("username", "Unknown"))
            result_text += f"• {channel_name}: {failed['error'][:50]}...\n"
    else:
        # All failed
        result_text = " **Publishing Failed**\n\n"
        result_text += "Failed to publish to any channels:\n"
        for failed in failed_channels:
            channel_name = failed["channel"].get("title", failed["channel"].get("username", "Unknown"))
            result_text += f"• {channel_name}: {failed['error'][:50]}...\n"
    
    # Show results with better error handling
    try:
        await message.edit_text(result_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as edit_error:
        # If editing fails, send a new message
        await message.answer(result_text, parse_mode=ParseMode.MARKDOWN)
    if success_count > 0:
        # Clear post data after successful publish
        from utils.data_store import clear_user_data
        clear_user_data(actual_user_id)
        
        # Return to main menu
        from .start import cmd_back
        await cmd_back(message)
    else:
        # Return to post menu if all failed
        from .post_menu import show_post_menu
        await show_post_menu(message)
