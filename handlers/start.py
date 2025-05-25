"""
Start command handler with enhanced welcome message and developer info
"""
from aiogram import types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from constants import router, DEVELOPER_USERNAME, DEVELOPER_CHANNEL
from db import db
from utils.keyboards import get_main_menu_keyboard

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Create enhanced keyboard with developer button
    keyboard = get_main_menu_keyboard()

    # Create inline keyboard for developer info
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👨‍💻 Developer", 
                url=f"https://t.me/{DEVELOPER_USERNAME}"
            ),
            InlineKeyboardButton(
                text="📢 Updates Channel", 
                url=f"https://t.me/{DEVELOPER_CHANNEL[1:]}"
            )
        ]
    ])

    # Enhanced welcome message
    welcome_text = (
        f"🎉 **Welcome, {message.from_user.full_name}!** 🎉\n\n"
        
        f"🤖 **PostBot** - Your Advanced Channel Management Assistant\n\n"
        
        f"✨ **What I can do for you:**\n"
        f"🌟 Create rich, professional posts with text, media & buttons\n"
        f"📤 Publish to multiple channels simultaneously\n"
        f"✏️ Edit existing posts with live preview\n"
        f"🔗 Manage interactive buttons and links\n"
        f"📷 Handle photos, videos, documents & media groups\n"
        f"⚙️ Advanced settings: pin posts, notifications, link previews\n\n"
        
        f"🚀 **Quick Start:**\n"
        f"1. Use `/connect @yourchannel` to link your channel\n"
        f"2. Click '🌟 Create Post 🌟' to start\n"
        f"3. Add content, preview, and publish!\n\n"
        
        f"💡 **Pro Tips:**\n"
        f"• Use '✏️ Edit Post' to modify published content\n"
        f"• Button format: `Text - URL | Text2 - URL2`\n"
        f"• Preview before publishing for best results\n\n"
        
        f"🔧 **Need Help?**\n"
        f"Join our updates channel or contact the developer below!"
    )

    # Send the enhanced welcome message
    await message.answer(
        welcome_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )
    
    # Send developer info with inline buttons
    await message.answer(
        "👨‍💻 **Developer & Support**",
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

    # Update user information in the MongoDB database
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {
            "$set": {
                "user_id": message.from_user.id,
                "username": message.from_user.username,
                "full_name": message.from_user.full_name,
                "first_seen": message.date
            }
        },
        upsert=True,
    )

@router.message(lambda message: message.text == "🔙 Back")
async def cmd_back(message: types.Message):
    # Clear any ongoing post data
    from utils.data_store import clear_user_data
    clear_user_data(message.from_user.id)

    # Re-send the original keyboard after returning
    keyboard = get_main_menu_keyboard()

    await message.answer(
        f"🏠 **Main Menu**\n\n"
        f"Welcome back, **{message.from_user.full_name}**!\n"
        f"Choose an option to continue:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )

@router.message(lambda message: message.text == "👨‍💻 Developer Info")
async def cmd_developer_info(message: types.Message):
    """Show developer information"""
    
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💬 Contact Developer", 
                url=f"https://t.me/{DEVELOPER_USERNAME}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📢 Join Updates Channel", 
                url=f"https://t.me/{DEVELOPER_CHANNEL[1:]}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⭐ Rate on GitHub", 
                url="https://github.com/DevIncognito/postbot"
            )
        ]
    ])
    
    dev_text = (
        f"👨‍💻 **About the Developer**\n\n"
        
        f"**Name:** DevIncognito\n"
        f"**Telegram:** @{DEVELOPER_USERNAME}\n"
        f"**Channel:** {DEVELOPER_CHANNEL}\n\n"
        
        f"🚀 **Passionate Bot Developer**\n"
        f"Creating powerful Telegram bots that make life easier!\n\n"
        
        f"🌟 **Open Source Contributor**\n"
        f"This bot is open source and free to use!\n\n"
        
        f"📞 **Get in Touch:**\n"
        f"Feel free to contact me for custom bot development,\n"
        f"feature requests, or just to say hi! 👋"
    )
    
    await message.answer(
        dev_text,
        reply_markup=inline_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(lambda message: message.text == "✏️ Edit Post")
async def cmd_edit_post_menu(message: types.Message):
    """Handle Edit Post button from main menu"""
    from .edit_post import cmd_edit_post
    await cmd_edit_post(message)
