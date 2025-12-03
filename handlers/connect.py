"""
Connect channel handler for PostBot
Handles connecting and disconnecting channels
"""
from aiogram import types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import html

from constants import router
from db import db
from config import Config
from utils.logger import logger, log_user_action

@router.message(Command("connect"))
async def cmd_connect(message: types.Message):
    """Connect a channel to the bot"""
    # Check if user has reached the limit
    user = await db.users.find_one({"user_id": message.from_user.id})
    connected_channels = user.get("connected_channels", []) if user else []
    
    if len(connected_channels) >= Config.MAX_CHANNELS_PER_USER and not Config.is_admin(message.from_user.id):
        await message.reply(
            f"<b>Limit Reached</b>\n\n"
            f"You have reached the maximum limit of {Config.MAX_CHANNELS_PER_USER} connected channels.\n"
            "Please disconnect a channel before adding a new one.",
            parse_mode=ParseMode.HTML
        )
        return

    command_parts = message.text.split()
    if len(command_parts) < 2:
        await message.reply(
            "<b>Connect to Channel</b>\n\n"
            "Please provide the username of the channel to connect.\n"
            "Usage: <code>/connect @channelname</code> or <code>/connect channelname</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    original_input = command_parts[1]
    channel_identifier = original_input
    
    # Normalize input
    if not channel_identifier.startswith("@") and not channel_identifier.startswith("-100"):
        if channel_identifier.replace("-", "").isdigit():
            # It's a chat ID
            pass
        else:
            # Assume it's a username without @
            channel_identifier = f"@{channel_identifier}"
            
    status_msg = await message.reply("Checking channel...")
    
    try:
        # Get chat info
        chat_info = await message.bot.get_chat(channel_identifier)
        
        # Verify it's a channel
        if chat_info.type != "channel":
            current_type = chat_info.type.title()
            title = html.escape(chat_info.title or str(channel_identifier))
            await message.reply(
                "<b>Only Channels Supported</b>\n\n"
                f"<b>{title}</b> is a <b>{current_type}</b>.\n\n"
                "This bot only supports channels:\n"
                "• Public channels (@channelname)\n"
                "• Private channels (with chat ID)\n\n"
                "Please use a channel instead of groups or private chats.",
                parse_mode=ParseMode.HTML
            )
            return
            
        # Check if bot is admin
        try:
            bot_member = await message.bot.get_chat_member(chat_info.id, message.bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                title = html.escape(chat_info.title or str(channel_identifier))
                await message.reply(
                    "<b>Bot Not Admin</b>\n\n"
                    f"Bot must be an admin in <b>{title}</b> to connect.\n"
                    "Please promote the bot and try again.",
                    parse_mode=ParseMode.HTML
                )
                return
        except Exception as member_error:
            title = html.escape(chat_info.title or str(channel_identifier))
            error_msg = html.escape(str(member_error))
            await message.reply(
                "<b>Permission Check Failed</b>\n\n"
                f"Cannot verify bot permissions in <b>{title}</b>.\n\n"
                f"Error: {error_msg}\n\n"
                "Please ensure:\n"
                "• The bot is added to the channel\n"
                "• The bot has admin privileges\n"
                "• The channel allows bots",
                parse_mode=ParseMode.HTML
            )
            return
            
        # Check if already connected by this user
        for channel in connected_channels:
            if str(channel.get("chat_id")) == str(chat_info.id):
                title = html.escape(chat_info.title or str(channel_identifier))
                await message.reply(
                    f"<b>Already Connected</b>\n\n"
                    f"You are already connected to <b>{title}</b>",
                    parse_mode=ParseMode.HTML
                )
                return
                
        # Add to database
        new_channel = {
            "chat_id": chat_info.id,
            "title": chat_info.title,
            "username": chat_info.username,
            "type": chat_info.type,
            "connected_at": message.date
        }
        
        await db.users.update_one(
            {"user_id": message.from_user.id},
            {"$push": {"connected_channels": new_channel}}
        )
        
        # Update current channels list for response
        connected_channels.append(new_channel)
        
        title = html.escape(chat_info.title or str(channel_identifier))
        await message.reply(
            f"<b>Successfully Connected!</b>\n\n"
            f"Connected to: <b>{title}</b>\n"
            f"Type: <b>{chat_info.type.title()}</b>\n"
            f"Total connected channels: <b>{len(connected_channels)}</b>",
            parse_mode=ParseMode.HTML
        )
        
        log_user_action(message.from_user.id, "CONNECT_CHANNEL", f"Channel: {chat_info.id}")
        
    except Exception as e:
        error_message = str(e).lower()
        if "chat not found" in error_message or "chat_not_found" in error_message:
            safe_input = html.escape(original_input)
            await message.reply(
                "<b>Channel Not Found</b>\n\n"
                f"Could not find: <b>{safe_input}</b>\n\n"
                "Please check:\n"
                "• Channel exists and is accessible\n"
                "• Correct username format (@channelname)\n"
                "• For private channels, use the numeric chat ID\n"
                "• Bot has been added to the channel\n\n"
                "<b>Examples:</b>\n"
                "• <code>/connect @publicchannel</code>\n"
                "• <code>/connect -1001234567890</code> (for private channels)",
                parse_mode=ParseMode.HTML
            )
        elif "forbidden" in error_message or "not enough rights" in error_message:
            safe_input = html.escape(original_input)
            await message.reply(
                "<b>Access Forbidden</b>\n\n"
                f"Bot doesn't have access to <b>{safe_input}</b>\n\n"
                "Please ensure:\n"
                "• Bot is added to the channel\n"
                "• Bot has admin privileges\n"
                "• Channel allows bots",
                parse_mode=ParseMode.HTML
            )
        elif "bad request" in error_message:
            safe_input = html.escape(original_input)
            await message.reply(
                "<b>Invalid Request</b>\n\n"
                f"Invalid channel identifier: <b>{safe_input}</b>\n\n"
                "Please use:\n"
                "• Public channel: <code>@channelname</code>\n"
                "• Private channel: <code>-1001234567890</code>\n"
                "• Make sure the identifier is correct",
                parse_mode=ParseMode.HTML
            )
        else:
            error_msg = html.escape(str(e))
            await message.reply(
                "<b>Connection Failed</b>\n\n"
                f"Error: {error_msg}\n\n"
                "Please make sure:\n"
                "• The channel exists\n"
                "• The bot has access to it\n"
                "• The bot is an admin\n"
                "• The identifier is correct",
                parse_mode=ParseMode.HTML
            )
        logger.error(f"Connect channel error: {e}")
    finally:
        try:
            await status_msg.delete()
        except:
            pass

@router.message(Command("connected"))
async def cmd_connected(message: types.Message):
    """List connected channels"""
    user = await db.users.find_one({"user_id": message.from_user.id})
    connected_channels = user.get("connected_channels", []) if user else []
    
    if not connected_channels:
        await message.reply(
            "<b>No Connected Channels</b>\n\n"
            "You haven't connected any channels yet.\n"
            "Use <code>/connect</code> to add a channel.",
            parse_mode=ParseMode.HTML
        )
        return
    
    response = "<b>Connected Channels</b>\n\n"
    for i, channel in enumerate(connected_channels, 1):
        title = html.escape(channel.get('title', 'Unknown'))
        username = channel.get('username')
        chat_id = channel.get('chat_id')
        
        response += f"{i}. <b>{title}</b>\n"
        if username:
            response += f"   @{username}\n"
        else:
            response += f"   ID: {chat_id}\n"
        response += "\n"
        
    response += f"Total: {len(connected_channels)}/{Config.MAX_CHANNELS_PER_USER}"
    
    await message.reply(response, parse_mode=ParseMode.HTML)

@router.message(Command("disconnect"))
async def cmd_disconnect(message: types.Message):
    """Disconnect a channel"""
    user = await db.users.find_one({"user_id": message.from_user.id})
    connected_channels = user.get("connected_channels", []) if user else []
    
    if not connected_channels:
        await message.reply(
            "<b>No Channels to Disconnect</b>\n\n"
            "You don't have any connected channels.",
            parse_mode=ParseMode.HTML
        )
        return
        
    # If arguments provided, try to disconnect specific channel
    command_parts = message.text.split()
    if len(command_parts) > 1:
        target = command_parts[1]
        
        # Find channel to remove
        channel_to_remove = None
        for channel in connected_channels:
            if (str(channel.get('chat_id')) == target or 
                f"@{channel.get('username')}" == target or 
                channel.get('username') == target):
                channel_to_remove = channel
                break
        
        if channel_to_remove:
            await db.users.update_one(
                {"user_id": message.from_user.id},
                {"$pull": {"connected_channels": {"chat_id": channel_to_remove['chat_id']}}}
            )
            
            safe_title = html.escape(channel_to_remove.get('title', 'Unknown'))
            await message.reply(
                f"<b>Disconnected Successfully</b>\n\n"
                f"Removed: <b>{safe_title}</b>",
                parse_mode=ParseMode.HTML
            )
            log_user_action(message.from_user.id, "DISCONNECT_CHANNEL", f"Channel: {channel_to_remove['chat_id']}")
        else:
            safe_target = html.escape(target)
            await message.reply(
                f"<b>Channel Not Found</b>\n\n"
                f"Could not find connected channel: <b>{safe_target}</b>",
                parse_mode=ParseMode.HTML
            )
        return

    # Show interactive menu
    keyboard = []
    for channel in connected_channels:
        title = channel.get('title', channel.get('username', 'Unknown'))
        if len(title) > 30:
            title = title[:27] + "..."
        
        callback_data = f"disconnect_{channel.get('chat_id')}"
        keyboard.append([InlineKeyboardButton(text=f"❌ {title}", callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton(text="Cancel", callback_data="cancel_manage")])
    
    await message.reply(
        "<b>Disconnect Channel</b>\n\n"
        "Select a channel to disconnect:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(lambda query: query.data.startswith("disconnect_"))
async def handle_disconnect_channel(query: types.CallbackQuery):
    """Handle disconnect callback"""
    chat_id = query.data.replace("disconnect_", "")
    
    user = await db.users.find_one({"user_id": query.from_user.id})
    connected_channels = user.get("connected_channels", [])
    
    channel_to_remove = None
    for channel in connected_channels:
        if str(channel.get('chat_id')) == str(chat_id):
            channel_to_remove = channel
            break
    
    if channel_to_remove:
        await db.users.update_one(
            {"user_id": query.from_user.id},
            {"$pull": {"connected_channels": {"chat_id": channel_to_remove['chat_id']}}}
        )
        
        safe_title = html.escape(channel_to_remove.get('title', 'Unknown'))
        remaining = len(connected_channels) - 1
        
        await query.message.edit_text(
            f"<b>Disconnected Successfully!</b>\n\n"
            f"Disconnected from: <b>{safe_title}</b>\n"
            f"Remaining connected channels: <b>{remaining}</b>",
            parse_mode=ParseMode.HTML
        )
        log_user_action(query.from_user.id, "DISCONNECT_CHANNEL", f"Channel: {chat_id}")
    else:
        await query.message.edit_text(
            "<b>Error</b>\n\nChannel not found or already disconnected.",
            parse_mode=ParseMode.HTML
        )
    
    await query.answer()

@router.callback_query(lambda query: query.data == "cancel_manage")
async def handle_cancel_manage(query: types.CallbackQuery):
    """Cancel management action"""
    await query.message.edit_text("Action cancelled.")
    await query.answer("Cancelled")