from aiogram import types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from constants import router
from db import db


@router.message(Command("connect"))
async def cmd_connect(message: types.Message):
    # Get the channel username from the user's message
    command_parts = message.text.split(maxsplit=1)
    
    if len(command_parts) < 2:
        await message.reply(
            " **Connect to Channel**\n\n"
            "Please provide the username of the channel to connect.\n"
            "Usage: `/connect @channelname` or `/connect channelname`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    channel_username = command_parts[1].strip()
    original_input = channel_username
    
    # Clean the channel username - handle both @username and -chatid formats
    if channel_username.startswith('@'):
        channel_username = channel_username[1:]
    
    # Try to parse as chat ID first (for private groups/supergroups)
    chat_identifier = None
    if channel_username.startswith('-') or (channel_username.lstrip('-').isdigit()):
        try:
            chat_identifier = int(channel_username)
        except ValueError:
            chat_identifier = f"@{channel_username}"
    else:
        chat_identifier = f"@{channel_username}"

    try:
        # Get information about the chat (channel)
        chat_info = await message.bot.get_chat(chat_identifier)
        
        # Check if it's a channel (only allow channels, not groups/supergroups/private chats)
        if chat_info.type not in ['channel']:
            chat_type_names = {
                'private': 'Private Chat',
                'group': 'Group',
                'supergroup': 'Supergroup',
                'channel': 'Channel'
            }
            current_type = chat_type_names.get(chat_info.type, chat_info.type.title())
            
            await message.reply(
                " **Only Channels Supported**\n\n"
                f"**{chat_info.title or chat_identifier}** is a **{current_type}**.\n\n"
                "This bot only supports channels:\n"
                "• Public channels (@channelname)\n"
                "• Private channels (with chat ID)\n\n"
                "Please use a channel instead of groups or private chats.",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Check if the bot is an administrator in the channel
        try:
            bot_member = await message.bot.get_chat_member(chat_identifier, message.bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await message.reply(
                    " **Bot Not Admin**\n\n"
                    f"Bot must be an admin in **{chat_info.title or chat_identifier}** to connect.\n"
                    "Please promote the bot and try again.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        except Exception as member_error:
            await message.reply(
                " **Permission Check Failed**\n\n"
                f"Cannot verify bot permissions in **{chat_info.title or chat_identifier}**.\n\n"
                f"Error: {str(member_error)}\n\n"
                "Please ensure:\n"
                "• The bot is added to the channel\n"
                "• The bot has admin privileges\n"
                "• The channel allows bots",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
    except Exception as e:
        error_message = str(e).lower()
        
        if "chat not found" in error_message or "chat_not_found" in error_message:
            await message.reply(
                " **Channel Not Found**\n\n"
                f"Could not find: **{original_input}**\n\n"
                "Please check:\n"
                "• Channel exists and is accessible\n"
                "• Correct username format (@channelname)\n"
                "• For private channels, use the numeric chat ID\n"
                "• Bot has been added to the channel\n\n"
                "**Examples:**\n"
                "• `/connect @publicchannel`\n"
                "• `/connect -1001234567890` (for private channels)",
                parse_mode=ParseMode.MARKDOWN
            )
        elif "forbidden" in error_message or "not enough rights" in error_message:
            await message.reply(
                " **Access Forbidden**\n\n"
                f"Bot doesn't have access to **{original_input}**\n\n"
                "Please ensure:\n"
                "• Bot is added to the channel\n"
                "• Bot has admin privileges\n"
                "• Channel allows bots",
                parse_mode=ParseMode.MARKDOWN
            )
        elif "bad request" in error_message:
            await message.reply(
                " **Invalid Request**\n\n"
                f"Invalid channel identifier: **{original_input}**\n\n"
                "Please use:\n"
                "• Public channel: `@channelname`\n"
                "• Private channel: `-1001234567890`\n"
                "• Make sure the identifier is correct",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.reply(
                " **Connection Failed**\n\n"
                f"Error: {str(e)}\n\n"
                "Please make sure:\n"
                "• The channel exists\n"
                "• The bot has access to it\n"
                "• The bot is an admin\n"
                "• The identifier is correct",
                parse_mode=ParseMode.MARKDOWN
            )
        return

    # Get current user data
    user_info = await db.users.find_one({"user_id": message.from_user.id})
    current_channels = user_info.get("connected_channels", []) if user_info else []
    
    # Check if channel is already connected
    channel_data = {
        "username": str(chat_identifier),
        "title": chat_info.title or str(chat_identifier),
        "chat_id": chat_info.id,
        "type": chat_info.type
    }
    
    # Check if already connected
    for existing_channel in current_channels:
        if (existing_channel.get("username") == str(chat_identifier) or 
            existing_channel.get("chat_id") == chat_info.id):
            await message.reply(
                f" **Already Connected**\n\n"
                f"You are already connected to **{chat_info.title or chat_identifier}**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

    # Add new channel to the list
    current_channels.append(channel_data)
    
    # Update user information with connected channels
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {
            "$set": {
                "connected_channels": current_channels,
                # Keep backward compatibility
                "connected_chat": str(chat_identifier),
                "connected_channel": str(chat_identifier)
            }
        },
        upsert=True,
    )

    await message.reply(
        f" **Successfully Connected!**\n\n"
        f"Connected to: **{chat_info.title or chat_identifier}**\n"
        f"Type: **{chat_info.type.title()}**\n"
        f"Total connected channels: **{len(current_channels)}**",
        parse_mode=ParseMode.MARKDOWN
    )


@router.message(Command("connected"))
async def cmd_connected(message: types.Message):
    # Retrieve connected channels from the user's information
    user_info = await db.users.find_one({"user_id": message.from_user.id})
    
    if not user_info:
        await message.reply(
            " **No Connected Channels**\n\n"
            "You are not currently connected to any channels.\n"
            "Use `/connect @channelname` to connect to a channel.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    connected_channels = user_info.get("connected_channels", [])
    
    if not connected_channels:
        await message.reply(
            " **No Connected Channels**\n\n"
            "You are not currently connected to any channels.\n"
            "Use `/connect @channelname` to connect to a channel.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Create response with all connected channels
    response = " **Connected Channels**\n\n"
    
    for i, channel in enumerate(connected_channels, 1):
        title = channel.get("title", channel.get("username", "Unknown"))
        username = channel.get("username", "")
        response += f"{i}. **{title}**\n"
        if username:
            response += f"    {username}\n"
        response += "\n"
    
    response += f"**Total:** {len(connected_channels)} channel(s)\n\n"
    response += "Use `/disconnect @channelname` to disconnect from a channel"
    
    # Create inline keyboard for managing channels
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Disconnect Channel", callback_data="manage_channels")]
    ])
    
    await message.reply(
        response,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


@router.message(Command("disconnect"))
async def cmd_disconnect(message: types.Message):
    # Get the channel username from the user's message
    command_parts = message.text.split(maxsplit=1)
    
    if len(command_parts) < 2:
        await message.reply(
            " **Disconnect from Channel**\n\n"
            "Please provide the username or chat ID of the channel to disconnect.\n"
            "Usage: `/disconnect @channelname` or `/disconnect -1001234567890`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    channel_identifier = command_parts[1].strip()
    original_input = channel_identifier

    # Clean the channel identifier - handle both @username and -chatid formats
    if channel_identifier.startswith('@'):
        channel_identifier = channel_identifier[1:]
    
    # Try to parse as chat ID first (for private groups/supergroups)
    if channel_identifier.startswith('-') or (channel_identifier.lstrip('-').isdigit()):
        try:
            chat_id = int(channel_identifier)
            search_identifier = str(chat_id)
        except ValueError:
            search_identifier = f"@{channel_identifier}"
    else:
        search_identifier = f"@{channel_identifier}"

    # Get current user data
    user_info = await db.users.find_one({"user_id": message.from_user.id})
    
    if not user_info:
        await message.reply(
            " **No Connected Channels**\n\n"
            "You are not connected to any channels.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    current_channels = user_info.get("connected_channels", [])
    
    if not current_channels:
        await message.reply(
            " **No Connected Channels**\n\n"
            "You are not connected to any channels.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Find and remove the channel
    channel_found = False
    removed_channel_title = None
    updated_channels = []
    
    for channel in current_channels:
        # Check both username and chat_id for matching
        if (channel.get("username") == search_identifier or 
            str(channel.get("chat_id")) == search_identifier.replace('@', '') or
            str(channel.get("chat_id")) == channel_identifier):
            channel_found = True
            removed_channel_title = channel.get("title", search_identifier)
        else:
            updated_channels.append(channel)
    
    if not channel_found:
        await message.reply(
            f" **Channel Not Found**\n\n"
            f"You are not connected to {original_input}.\n"
            f"Use `/connected` to see your connected channels.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Update user information
    update_data = {"connected_channels": updated_channels}
    
    # Update backward compatibility fields
    if updated_channels:
        update_data["connected_chat"] = updated_channels[0]["username"]
        update_data["connected_channel"] = updated_channels[0]["username"]
    else:
        update_data["connected_chat"] = None
        update_data["connected_channel"] = None
    
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$set": update_data}
    )

    await message.reply(
        f" **Disconnected Successfully!**\n\n"
        f"Disconnected from: **{removed_channel_title or original_input}**\n"
        f"Remaining connected channels: **{len(updated_channels)}**",
        parse_mode=ParseMode.MARKDOWN
    )


@router.callback_query(lambda query: query.data == "manage_channels")
async def handle_manage_channels(query: types.CallbackQuery):
    await query.answer()
    
    # Get user's connected channels
    user_info = await db.users.find_one({"user_id": query.from_user.id})
    connected_channels = user_info.get("connected_channels", []) if user_info else []
    
    if not connected_channels:
        await query.message.edit_text(
            " **No Connected Channels**\n\n"
            "You are not connected to any channels.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Create inline keyboard for disconnecting channels
    keyboard = []
    for i, channel in enumerate(connected_channels):
        title = channel.get("title", channel.get("username", "Unknown"))
        keyboard.append([
            InlineKeyboardButton(
                text=f" {title}",
                callback_data=f"disconnect_{i}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text=" Cancel", callback_data="cancel_manage")])
    
    await query.message.edit_text(
        " **Select Channel to Disconnect**\n\n"
        "Choose a channel to disconnect from:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(lambda query: query.data.startswith("disconnect_"))
async def handle_disconnect_channel(query: types.CallbackQuery):
    await query.answer()
    
    try:
        channel_index = int(query.data.split("_")[1])
        
        # Get user's connected channels
        user_info = await db.users.find_one({"user_id": query.from_user.id})
        connected_channels = user_info.get("connected_channels", []) if user_info else []
        
        if channel_index >= len(connected_channels):
            await query.message.edit_text(
                " **Error**\n\n"
                "Channel not found.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Remove the selected channel
        removed_channel = connected_channels.pop(channel_index)
        removed_title = removed_channel.get("title", removed_channel.get("username", "Unknown"))
        
        # Update user information
        update_data = {"connected_channels": connected_channels}
        
        # Update backward compatibility fields
        if connected_channels:
            update_data["connected_chat"] = connected_channels[0]["username"]
            update_data["connected_channel"] = connected_channels[0]["username"]
        else:
            update_data["connected_chat"] = None
            update_data["connected_channel"] = None
        
        await db.users.update_one(
            {"user_id": query.from_user.id},
            {"$set": update_data}
        )

        await query.message.edit_text(
            f" **Disconnected Successfully!**\n\n"
            f"Disconnected from: **{removed_title}**\n"
            f"Remaining connected channels: **{len(connected_channels)}**",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except (ValueError, IndexError):
        await query.message.edit_text(
            " **Error**\n\n"
            "Invalid channel selection.",
            parse_mode=ParseMode.MARKDOWN
        )


@router.callback_query(lambda query: query.data == "cancel_manage")
async def handle_cancel_manage(query: types.CallbackQuery):
    await query.answer()
    
    # Recreate the original message instead of calling cmd_connected
    # to avoid issues with message context
    user_info = await db.users.find_one({"user_id": query.from_user.id})
    connected_channels = user_info.get("connected_channels", []) if user_info else []
    
    if not connected_channels:
        await query.message.edit_text(
            " **No Connected Channels**\n\n"
            "You are not connected to any channels.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Create response with all connected channels
    response = " **Connected Channels**\n\n"
    
    for i, channel in enumerate(connected_channels, 1):
        title = channel.get("title", channel.get("username", "Unknown"))
        username = channel.get("username", "")
        response += f"{i}. **{title}**\n"
        if username:
            response += f"    {username}\n"
        response += "\n"
    
    response += f"**Total:** {len(connected_channels)} channel(s)\n\n"
    response += "Use `/disconnect @channelname` to disconnect from a channel"
    
    # Create inline keyboard for managing channels
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Disconnect Channel", callback_data="manage_channels")]
    ])
    
    await query.message.edit_text(
        response,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )