"""
Statistics and misc handlers
"""
from aiogram import types
from aiogram.filters import Command

from constants import router
from db import db

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    try:
        total_users = await db.users.count_documents({})
        connected_users = await db.users.count_documents({"connected_chat": {"$exists": True}})
        
        await message.reply(
            f"📊 **Bot Statistics**\n\n"
            f"👥 Total users: {total_users}\n"
            f"🔗 Connected users: {connected_users}\n"
            f"📱 Active connections: {(connected_users/total_users*100):.1f}%" if total_users > 0 else "📱 Active connections: 0%",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.reply(f"❌ Error fetching stats: {str(e)}")
