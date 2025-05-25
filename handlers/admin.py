"""
Admin commands handler for PostBot
Advanced administrative functionality
"""
from aiogram import types
from aiogram.filters import Command
from datetime import datetime, timedelta
import asyncio

from constants import router
from db import db
from config import Config
from utils.logger import logger, log_user_action, log_system_event
from utils.backup import backup_manager

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Show admin menu"""
    if not Config.is_admin(message.from_user.id):
        await message.reply("❌ This command is only available for administrators.")
        return
    
    admin_text = (
        f"🔧 **Admin Panel**\n\n"
        f"**Available Commands:**\n"
        f"• `/analytics` - Detailed bot analytics\n"
        f"• `/backup` - Database backup management\n"
        f"• `/broadcast` - Send message to all users\n"
        f"• `/users` - User management\n"
        f"• `/system` - System information\n"
        f"• `/logs` - View recent logs\n"
        f"• `/config` - View configuration\n\n"
        f"**Quick Stats:**\n"
        f"• Total users: {await db.users.count_documents({}):,}\n"
        f"• Active features: {sum(Config.get_feature_status().values())}/3\n"
        f"• Admin ID: `{message.from_user.id}`"
    )
    
    await message.reply(admin_text, parse_mode="Markdown")
    log_user_action(message.from_user.id, "ADMIN_PANEL_ACCESS")

@router.message(Command("backup"))
async def cmd_backup(message: types.Message):
    """Backup management commands"""
    if not Config.is_admin(message.from_user.id):
        await message.reply("❌ This command is only available for administrators.")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args or args[0] == "list":
        # List backups
        backups = await backup_manager.list_backups()
        stats = await backup_manager.get_backup_stats()
        
        if not backups:
            await message.reply("📦 No backups found.")
            return
        
        backup_text = (
            f"📦 **Backup Management**\n\n"
            f"**Statistics:**\n"
            f"• Total backups: {stats['total_backups']}\n"
            f"• Total size: {stats['total_size_mb']} MB\n"
            f"• Latest: {stats['latest_backup'][:16]}\n\n"
            f"**Recent Backups:**\n"
        )
        
        for backup in backups[:5]:  # Show last 5 backups
            created = backup['created_at'][:16].replace('T', ' ')
            size = backup['size_mb']
            compressed = "🗜️" if backup['compressed'] else "📄"
            backup_text += f"• {compressed} {backup['filename']} ({size} MB) - {created}\n"
        
        backup_text += f"\n**Commands:**\n"
        backup_text += f"• `/backup create` - Create new backup\n"
        backup_text += f"• `/backup cleanup` - Remove old backups\n"
        
        await message.reply(backup_text, parse_mode="Markdown")
    
    elif args[0] == "create":
        # Create backup
        status_msg = await message.reply("🔄 Creating backup...")
        
        try:
            backup_file = await backup_manager.create_backup(compress=True)
            file_size = (await backup_manager.list_backups())[0]['size_mb']
            
            await status_msg.edit_text(
                f"✅ **Backup Created Successfully**\n\n"
                f"📁 File: `{backup_file.split('/')[-1]}`\n"
                f"📊 Size: {file_size} MB\n"
                f"🕐 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode="Markdown"
            )
            
            log_user_action(message.from_user.id, "BACKUP_CREATE", f"Size: {file_size}MB")
            
        except Exception as e:
            await status_msg.edit_text(f"❌ Backup failed: {str(e)}")
            logger.error(f"Manual backup failed: {e}")
    
    elif args[0] == "cleanup":
        # Cleanup old backups
        status_msg = await message.reply("🧹 Cleaning up old backups...")
        
        try:
            deleted_count = await backup_manager.cleanup_old_backups()
            
            if deleted_count > 0:
                await status_msg.edit_text(
                    f"✅ **Cleanup Completed**\n\n"
                    f"🗑️ Deleted: {deleted_count} old backup files\n"
                    f"📅 Retention: {Config.BACKUP_RETENTION} days"
                )
            else:
                await status_msg.edit_text("✅ No old backups to clean up.")
            
            log_user_action(message.from_user.id, "BACKUP_CLEANUP", f"Deleted: {deleted_count}")
            
        except Exception as e:
            await status_msg.edit_text(f"❌ Cleanup failed: {str(e)}")
            logger.error(f"Backup cleanup failed: {e}")
    
    else:
        await message.reply(
            "❓ **Backup Commands:**\n"
            "• `/backup list` - List all backups\n"
            "• `/backup create` - Create new backup\n"
            "• `/backup cleanup` - Remove old backups"
        )

@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    """Broadcast message to all users"""
    if not Config.is_admin(message.from_user.id):
        await message.reply("❌ This command is only available for administrators.")
        return
    
    # Check if message has content to broadcast
    if len(message.text.split(maxsplit=1)) < 2:
        await message.reply(
            "📢 **Broadcast Usage:**\n"
            "`/broadcast <message>`\n\n"
            "**Example:**\n"
            "`/broadcast 🎉 New feature released! Check it out with /start`",
            parse_mode="Markdown"
        )
        return
    
    broadcast_text = message.text.split(maxsplit=1)[1]
    
    # Confirmation
    confirm_text = (
        f"📢 **Confirm Broadcast**\n\n"
        f"**Message Preview:**\n"
        f"{broadcast_text}\n\n"
        f"**Will send to:** All registered users\n"
        f"**Estimated recipients:** {await db.users.count_documents({}):,}\n\n"
        f"Reply with `YES` to confirm or `NO` to cancel."
    )
    
    await message.reply(confirm_text, parse_mode="Markdown")
    
    # Wait for confirmation (simplified - in production, use proper state management)
    try:
        confirmation = await message.bot.wait_for_message(
            chat_id=message.chat.id,
            timeout=30
        )
        
        if confirmation.text.upper() == "YES":
            await start_broadcast(message, broadcast_text)
        else:
            await message.reply("❌ Broadcast cancelled.")
    except:
        await message.reply("⏰ Broadcast timed out. Cancelled.")

async def start_broadcast(message: types.Message, broadcast_text: str):
    """Start the broadcast process"""
    status_msg = await message.reply("🔄 Starting broadcast...")
    
    try:
        users = db.users.find({}, {"user_id": 1})
        sent_count = 0
        failed_count = 0
        
        async for user in users:
            try:
                await message.bot.send_message(
                    chat_id=user["user_id"],
                    text=f"📢 **Announcement**\n\n{broadcast_text}",
                    parse_mode="Markdown"
                )
                sent_count += 1
                
                # Rate limiting
                if sent_count % 20 == 0:
                    await asyncio.sleep(1)
                    await status_msg.edit_text(
                        f"🔄 Broadcasting... Sent: {sent_count:,}"
                    )
                
            except Exception as e:
                failed_count += 1
                if "bot was blocked" not in str(e).lower():
                    logger.warning(f"Broadcast failed to {user['user_id']}: {e}")
        
        # Final status
        await status_msg.edit_text(
            f"✅ **Broadcast Completed**\n\n"
            f"📤 Sent: {sent_count:,}\n"
            f"❌ Failed: {failed_count:,}\n"
            f"📊 Success rate: {(sent_count/(sent_count+failed_count)*100):.1f}%" if (sent_count + failed_count) > 0 else "📊 Success rate: 0%"
        )
        
        log_user_action(
            message.from_user.id, 
            "BROADCAST_SENT", 
            f"Sent: {sent_count}, Failed: {failed_count}"
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Broadcast failed: {str(e)}")
        logger.error(f"Broadcast failed: {e}")

@router.message(Command("users"))
async def cmd_users(message: types.Message):
    """User management commands"""
    if not Config.is_admin(message.from_user.id):
        await message.reply("❌ This command is only available for administrators.")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args or args[0] == "stats":
        # User statistics
        total_users = await db.users.count_documents({})
        
        # Time-based stats
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        today_users = await db.users.count_documents({"joined_date": {"$gte": today}})
        week_users = await db.users.count_documents({"joined_date": {"$gte": week_ago}})
        month_users = await db.users.count_documents({"joined_date": {"$gte": month_ago}})
        
        # Active users
        active_users = await db.users.count_documents({
            "last_activity": {"$gte": week_ago}
        })
        
        user_stats = (
            f"👥 **User Management**\n\n"
            f"**Overview:**\n"
            f"• Total users: {total_users:,}\n"
            f"• Active (7d): {active_users:,}\n"
            f"• Activity rate: {(active_users/total_users*100):.1f}%\n\n" if total_users > 0 else "• Activity rate: 0%\n\n"
            f"**Growth:**\n"
            f"• Today: +{today_users:,}\n"
            f"• This week: +{week_users:,}\n"
            f"• This month: +{month_users:,}\n\n"
            f"**Commands:**\n"
            f"• `/users find <user_id>` - Find user info\n"
            f"• `/users recent` - Show recent users\n"
            f"• `/users active` - Show active users"
        )
        
        await message.reply(user_stats, parse_mode="Markdown")
    
    elif args[0] == "find" and len(args) > 1:
        # Find specific user
        try:
            user_id = int(args[1])
            user = await db.users.find_one({"user_id": user_id})
            
            if user:
                joined = user.get('joined_date', 'Unknown')
                if isinstance(joined, datetime):
                    joined = joined.strftime('%Y-%m-%d %H:%M')
                
                last_activity = user.get('last_activity', 'Unknown')
                if isinstance(last_activity, datetime):
                    last_activity = last_activity.strftime('%Y-%m-%d %H:%M')
                
                user_info = (
                    f"👤 **User Information**\n\n"
                    f"**ID:** `{user['user_id']}`\n"
                    f"**Username:** @{user.get('username', 'N/A')}\n"
                    f"**First Name:** {user.get('first_name', 'N/A')}\n"
                    f"**Joined:** {joined}\n"
                    f"**Last Activity:** {last_activity}\n"
                    f"**Connected Chat:** {user.get('connected_chat', 'None')}"
                )
                
                await message.reply(user_info, parse_mode="Markdown")
            else:
                await message.reply(f"❌ User with ID `{user_id}` not found.")
                
        except ValueError:
            await message.reply("❌ Invalid user ID. Please provide a numeric user ID.")
    
    elif args[0] == "recent":
        # Show recent users
        recent_users = db.users.find({}).sort("joined_date", -1).limit(10)
        
        users_text = "👥 **Recent Users (Last 10):**\n\n"
        async for user in recent_users:
            joined = user.get('joined_date', datetime.now())
            if isinstance(joined, datetime):
                joined = joined.strftime('%m-%d %H:%M')
            
            username = f"@{user.get('username', 'N/A')}"
            users_text += f"• {user['user_id']} | {username} | {joined}\n"
        
        await message.reply(users_text, parse_mode="Markdown")
    
    else:
        await message.reply(
            "❓ **User Commands:**\n"
            "• `/users stats` - User statistics\n"
            "• `/users find <user_id>` - Find user info\n"
            "• `/users recent` - Show recent users"
        )

@router.message(Command("system"))
async def cmd_system(message: types.Message):
    """Show system information"""
    if not Config.is_admin(message.from_user.id):
        await message.reply("❌ This command is only available for administrators.")
        return
    
    import psutil
    import platform
    from datetime import datetime
    
    # System info
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Bot uptime (simplified)
    uptime = "Unknown"  # In production, track bot start time
    
    system_info = (
        f"🖥️ **System Information**\n\n"
        f"**Platform:**\n"
        f"• OS: {platform.system()} {platform.release()}\n"
        f"• Python: {platform.python_version()}\n"
        f"• Architecture: {platform.machine()}\n\n"
        f"**Resources:**\n"
        f"• CPU Usage: {cpu_percent}%\n"
        f"• RAM Usage: {memory.percent}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)\n"
        f"• Disk Usage: {disk.percent}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)\n\n"
        f"**Configuration:**\n"
        f"• Database: {Config.DATABASE_NAME}\n"
        f"• Log Level: {Config.LOG_LEVEL}\n"
        f"• Max Channels/User: {Config.MAX_CHANNELS_PER_USER}\n"
        f"• Backup Enabled: {'✅' if Config.ENABLE_BACKUP else '❌'}\n"
        f"• Analytics Enabled: {'✅' if Config.ENABLE_ANALYTICS else '❌'}"
    )
    
    await message.reply(system_info, parse_mode="Markdown")
    log_user_action(message.from_user.id, "SYSTEM_INFO_ACCESS")
