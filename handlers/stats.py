"""
Statistics and analytics handlers
"""
from aiogram import types
from aiogram.filters import Command
from datetime import datetime, timedelta
import asyncio

from constants import router
from db import db
from config import Config

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Show basic bot statistics"""
    try:
        # Basic stats
        total_users = await db.users.count_documents({})
        connected_users = await db.users.count_documents({"connected_chat": {"$exists": True}})
        
        # Time-based stats
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        today_users = await db.users.count_documents({"joined_date": {"$gte": today}})
        week_users = await db.users.count_documents({"joined_date": {"$gte": week_ago}})
        
        # Post stats (if posts collection exists)
        try:
            total_posts = await db.posts.count_documents({})
            today_posts = await db.posts.count_documents({"created_at": {"$gte": today}})
        except:
            total_posts = 0
            today_posts = 0
        
        stats_text = (
            f" **Bot Statistics**\n\n"
            f" **Users**\n"
            f"• Total users: {total_users:,}\n"
            f"• Connected users: {connected_users:,}\n"
            f"• New today: {today_users:,}\n"
            f"• New this week: {week_users:,}\n"
            f"• Connection rate: {(connected_users/total_users*100):.1f}%\n\n" if total_users > 0 else "• Connection rate: 0%\n\n"
            f" **Posts**\n"
            f"• Total posts: {total_posts:,}\n"
            f"• Posts today: {today_posts:,}\n\n"
            f" **System**\n"
            f"• Analytics: {'' if Config.ENABLE_ANALYTICS else ''}\n"
            f"• Backup: {'' if Config.ENABLE_BACKUP else ''}\n"
            f"• Notifications: {'' if Config.ENABLE_NOTIFICATIONS else ''}"
        )
        
        await message.reply(stats_text, parse_mode="Markdown")
        
    except Exception as e:
        await message.reply(f" Error fetching stats: {str(e)}")

@router.message(Command("analytics"))
async def cmd_analytics(message: types.Message):
    """Show detailed analytics (admin only)"""
    if not Config.is_admin(message.from_user.id):
        await message.reply(" This command is only available for administrators.")
        return
    
    try:
        # Get detailed analytics
        analytics = await get_detailed_analytics()
        
        analytics_text = (
            f" **Detailed Analytics**\n\n"
            f" **Daily Growth**\n"
            f"• Today: +{analytics['daily']['today']:,} users\n"
            f"• Yesterday: +{analytics['daily']['yesterday']:,} users\n"
            f"• Average/day: {analytics['daily']['average']:.1f} users\n\n"
            f" **Weekly Stats**\n"
            f"• This week: +{analytics['weekly']['current']:,} users\n"
            f"• Last week: +{analytics['weekly']['previous']:,} users\n"
            f"• Growth: {analytics['weekly']['growth']:+.1f}%\n\n"
            f" **Activity**\n"
            f"• Active users (7d): {analytics['activity']['active_7d']:,}\n"
            f"• Posts created (7d): {analytics['activity']['posts_7d']:,}\n"
            f"• Average posts/user: {analytics['activity']['avg_posts_per_user']:.1f}\n\n"
            f" **Top Features**\n"
            f"• Most used: {analytics['features']['most_used']}\n"
            f"• Least used: {analytics['features']['least_used']}"
        )
        
        await message.reply(analytics_text, parse_mode="Markdown")
        
    except Exception as e:
        await message.reply(f" Error fetching analytics: {str(e)}")

async def get_detailed_analytics():
    """Get detailed analytics data"""
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    prev_week = week_ago - timedelta(days=7)
    
    # Daily stats
    today_users = await db.users.count_documents({"joined_date": {"$gte": today}})
    yesterday_users = await db.users.count_documents({
        "joined_date": {"$gte": yesterday, "$lt": today}
    })
    
    # Weekly stats
    week_users = await db.users.count_documents({"joined_date": {"$gte": week_ago}})
    prev_week_users = await db.users.count_documents({
        "joined_date": {"$gte": prev_week, "$lt": week_ago}
    })
    
    # Calculate growth
    growth = ((week_users - prev_week_users) / prev_week_users * 100) if prev_week_users > 0 else 0
    
    # Activity stats
    active_users = await db.users.count_documents({
        "last_activity": {"$gte": week_ago}
    })
    
    try:
        posts_7d = await db.posts.count_documents({"created_at": {"$gte": week_ago}})
        total_posts = await db.posts.count_documents({})
        total_users = await db.users.count_documents({})
        avg_posts = total_posts / total_users if total_users > 0 else 0
    except:
        posts_7d = 0
        avg_posts = 0
    
    # Average daily users (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    thirty_day_users = await db.users.count_documents({"joined_date": {"$gte": thirty_days_ago}})
    avg_daily = thirty_day_users / 30
    
    return {
        "daily": {
            "today": today_users,
            "yesterday": yesterday_users,
            "average": avg_daily
        },
        "weekly": {
            "current": week_users,
            "previous": prev_week_users,
            "growth": growth
        },
        "activity": {
            "active_7d": active_users,
            "posts_7d": posts_7d,
            "avg_posts_per_user": avg_posts
        },
        "features": {
            "most_used": "Channel Connection",  # This could be dynamic based on usage data
            "least_used": "Advanced Settings"   # This could be dynamic based on usage data
        }
    }
