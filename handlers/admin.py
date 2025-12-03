"""
Admin commands handler for PostBot
Advanced administrative functionality
"""
from aiogram import types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import asyncio
import uuid
import html

from constants import router
from db import db
from config import Config
from utils.logger import logger, log_user_action, log_system_event
from utils.backup import backup_manager

# Store broadcast sessions temporarily
broadcast_sessions = {}

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Show admin menu"""
    if not Config.is_admin(message.from_user.id):
        await message.reply("This command is only available for administrators.")
        return
    
    try:
        total_users = await db.users.count_documents({})
        feature_status = Config.get_feature_status()
        active_features = sum(feature_status.values()) if feature_status else 0
        
        admin_text = (
            f"<b>Admin Panel</b>\n\n"
            f"<b>Available Commands:</b>\n"
            f"• <code>/analytics</code> - Detailed bot analytics\n"
            f"• <code>/backup</code> - Database backup management\n"
            f"• <code>/broadcast</code> - Send message to all users\n"
            f"• <code>/users</code> - User management\n"
            f"• <code>/system</code> - System information\n"
            f"• <code>/logs</code> - View recent logs\n"
            f"• <code>/config</code> - View configuration\n\n"
            f"<b>Quick Stats:</b>\n"
            f"• Total users: {total_users:,}\n"
            f"• Active features: {active_features}/3\n"
            f"• Admin ID: <code>{message.from_user.id}</code>"
        )
        
        await message.reply(admin_text, parse_mode=ParseMode.HTML)
        log_user_action(message.from_user.id, "ADMIN_PANEL_ACCESS")
        
    except Exception as e:
        error_msg = html.escape(str(e))
        await message.reply(f"Error loading admin panel: {error_msg}")
        logger.error(f"Admin panel error: {e}")

@router.message(Command("backup"))
async def cmd_backup(message: types.Message):
    """Backup management commands"""
    if not Config.is_admin(message.from_user.id):
        await message.reply("This command is only available for administrators.")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    try:
        if not args or args[0] == "list":
            # List backups
            backups = await backup_manager.list_backups()
            stats = await backup_manager.get_backup_stats()
            
            if not backups:
                await message.reply("No backups found.")
                return
            
            backup_text = (
                f"<b>Backup Management</b>\n\n"
                f"<b>Statistics:</b>\n"
                f"• Total backups: {stats.get('total_backups', 0)}\n"
                f"• Total size: {stats.get('total_size_mb', 0)} MB\n"
                f"• Latest: {stats.get('latest_backup', 'N/A')[:16]}\n\n"
                f"<b>Recent Backups:</b>\n"
            )
            
            for backup in backups[:5]:  # Show last 5 backups
                created = backup.get('created_at', '')[:16].replace('T', ' ')
                size = backup.get('size_mb', 0)
                compressed = "" if backup.get('compressed') else ""
                filename = html.escape(backup.get('filename', 'Unknown'))
                backup_text += f"• {compressed} {filename} ({size} MB) - {created}\n"
            
            backup_text += f"\n<b>Commands:</b>\n"
            backup_text += f"• <code>/backup create</code> - Create new backup\n"
            backup_text += f"• <code>/backup cleanup</code> - Remove old backups\n"
            
            await message.reply(backup_text, parse_mode=ParseMode.HTML)
        
        elif args[0] == "create":
            # Create backup
            status_msg = await message.reply("Creating backup...")
            
            try:
                backup_file = await backup_manager.create_backup(compress=True)
                backups = await backup_manager.list_backups()
                file_size = backups[0].get('size_mb', 0) if backups else 0
                
                safe_filename = html.escape(backup_file.split('/')[-1] if backup_file else 'Unknown')
                
                await status_msg.edit_text(
                    f"<b>Backup Created Successfully</b>\n\n"
                    f"File: <code>{safe_filename}</code>\n"
                    f"Size: {file_size} MB\n"
                    f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode=ParseMode.HTML
                )
                
                log_user_action(message.from_user.id, "BACKUP_CREATE", f"Size: {file_size}MB")
                
            except Exception as e:
                error_msg = html.escape(str(e))
                await status_msg.edit_text(f"Backup failed: {error_msg}")
                logger.error(f"Manual backup failed: {e}")
        
        elif args[0] == "cleanup":
            # Cleanup old backups
            status_msg = await message.reply("Cleaning up old backups...")
            
            try:
                deleted_count = await backup_manager.cleanup_old_backups()
                retention_days = getattr(Config, 'BACKUP_RETENTION', 7)
                
                if deleted_count > 0:
                    await status_msg.edit_text(
                        f"<b>Cleanup Completed</b>\n\n"
                        f"Deleted: {deleted_count} old backup files\n"
                        f"Retention: {retention_days} days",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await status_msg.edit_text("No old backups to clean up.")
                
                log_user_action(message.from_user.id, "BACKUP_CLEANUP", f"Deleted: {deleted_count}")
                
            except Exception as e:
                error_msg = html.escape(str(e))
                await status_msg.edit_text(f"Cleanup failed: {error_msg}")
                logger.error(f"Backup cleanup failed: {e}")
        
        else:
            await message.reply(
                "<b>Backup Commands:</b>\n"
                "• <code>/backup list</code> - List all backups\n"
                "• <code>/backup create</code> - Create new backup\n"
                "• <code>/backup cleanup</code> - Remove old backups",
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        error_msg = html.escape(str(e))
        await message.reply(f"Backup command error: {error_msg}")
        logger.error(f"Backup command error: {e}")

@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    """Broadcast message to all users"""
    if not Config.is_admin(message.from_user.id):
        await message.reply("This command is only available for administrators.")
        return
    
    # Check if replying to a message
    if message.reply_to_message:
        broadcast_text = message.reply_to_message.text or message.reply_to_message.caption
        if not broadcast_text:
            await message.reply("The replied message must contain text or caption.")
            return
    else:
        # Check if message has content to broadcast
        if len(message.text.split(maxsplit=1)) < 2:
            await message.reply(
                "<b>Broadcast Usage:</b>\n"
                "• <code>/broadcast &lt;message&gt;</code> - Broadcast text message\n"
                "• Reply to a message with <code>/broadcast</code> - Broadcast that message\n\n"
                "<b>Example:</b>\n"
                "<code>/broadcast New feature released! Check it out with /start</code>",
                parse_mode=ParseMode.HTML
            )
            return
        broadcast_text = message.text.split(maxsplit=1)[1]
    
    try:
        total_users = await db.users.count_documents({})
        
        # Create unique session ID
        session_id = str(uuid.uuid4())
        broadcast_sessions[session_id] = {
            'admin_id': message.from_user.id,
            'chat_id': message.chat.id,
            'message': broadcast_text,
            'is_reply': bool(message.reply_to_message),
            'reply_message': message.reply_to_message,
            'created_at': datetime.now()
        }
        
        # Create confirmation keyboard
        keyboard = InlineKeyboardBuilder()
        keyboard.add(
            types.InlineKeyboardButton(text="Yes, Send", callback_data=f"broadcast_yes_{session_id}"),
            types.InlineKeyboardButton(text="No, Cancel", callback_data=f"broadcast_no_{session_id}")
        )
        keyboard.adjust(2)
        
        # Confirmation message
        safe_preview = html.escape(broadcast_text[:200]) + "..." if len(broadcast_text) > 200 else html.escape(broadcast_text)
        confirm_text = (
            f"<b>Confirm Broadcast</b>\n\n"
            f"<b>Message Preview:</b>\n"
            f"{safe_preview}\n\n"
            f"<b>Will send to:</b> All registered users\n"
            f"<b>Estimated recipients:</b> {total_users:,}\n\n"
            f"<b>Choose an option:</b>"
        )
        
        await message.reply(
            confirm_text, 
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.as_markup()
        )
        
    except Exception as e:
        error_msg = html.escape(str(e))
        await message.reply(f"Error preparing broadcast: {error_msg}")
        logger.error(f"Broadcast preparation error: {e}")

@router.callback_query(F.data.startswith("broadcast_"))
async def handle_broadcast_callback(callback: types.CallbackQuery):
    """Handle broadcast confirmation callbacks"""
    try:
        action, session_id = callback.data.split("_", 2)[1], callback.data.split("_", 2)[2]
        
        if session_id not in broadcast_sessions:
            await callback.answer("Broadcast session expired.", show_alert=True)
            return
        
        session = broadcast_sessions[session_id]
        
        # Verify admin
        if callback.from_user.id != session['admin_id']:
            await callback.answer("Only the admin who initiated this can confirm.", show_alert=True)
            return
        
        if action == "yes":
            await callback.answer("Starting broadcast...")
            await start_broadcast(callback, session)
        else:
            await callback.answer("Broadcast cancelled.")
            await callback.message.edit_text("Broadcast cancelled.")
        
        # Clean up session
        del broadcast_sessions[session_id]
        
    except Exception as e:
        await callback.answer(f"Error: {str(e)}", show_alert=True)
        logger.error(f"Broadcast callback error: {e}")

async def start_broadcast(callback: types.CallbackQuery, session: dict):
    """Start the broadcast process"""
    try:
        await callback.message.edit_text("Starting broadcast...")
        
        users_cursor = db.users.find({}, {"user_id": 1})
        sent_count = 0
        failed_count = 0
        blocked_count = 0
        
        async for user in users_cursor:
            try:
                user_id = user["user_id"]
                
                if session['is_reply'] and session['reply_message']:
                    # Forward the original message
                    if session['reply_message'].photo:
                        await callback.bot.send_photo(
                            chat_id=user_id,
                            photo=session['reply_message'].photo[-1].file_id,
                            caption=f"<b>Announcement</b>\n\n{html.escape(session['reply_message'].caption or '')}",
                            parse_mode=ParseMode.HTML
                        )
                    elif session['reply_message'].video:
                        await callback.bot.send_video(
                            chat_id=user_id,
                            video=session['reply_message'].video.file_id,
                            caption=f"<b>Announcement</b>\n\n{html.escape(session['reply_message'].caption or '')}",
                            parse_mode=ParseMode.HTML
                        )
                    elif session['reply_message'].document:
                        await callback.bot.send_document(
                            chat_id=user_id,
                            document=session['reply_message'].document.file_id,
                            caption=f"<b>Announcement</b>\n\n{html.escape(session['reply_message'].caption or '')}",
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        await callback.bot.send_message(
                            chat_id=user_id,
                            text=f"<b>Announcement</b>\n\n{html.escape(session['message'])}",
                            parse_mode=ParseMode.HTML
                        )
                else:
                    # Send text message
                    await callback.bot.send_message(
                        chat_id=user_id,
                        text=f"<b>Announcement</b>\n\n{html.escape(session['message'])}",
                        parse_mode=ParseMode.HTML
                    )
                
                sent_count += 1
                
                # Rate limiting and progress update
                if sent_count % 20 == 0:
                    await asyncio.sleep(1)
                    await callback.message.edit_text(
                        f"Broadcasting... Sent: {sent_count:,}"
                    )
                
            except Exception as e:
                error_str = str(e).lower()
                if "bot was blocked" in error_str or "user is deactivated" in error_str:
                    blocked_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"Broadcast failed to {user['user_id']}: {e}")
        
        # Final status
        total_attempts = sent_count + failed_count + blocked_count
        success_rate = (sent_count / total_attempts * 100) if total_attempts > 0 else 0
        
        await callback.message.edit_text(
            f"<b>Broadcast Completed</b>\n\n"
            f"Successfully sent: {sent_count:,}\n"
            f"Blocked/Inactive: {blocked_count:,}\n"
            f"Failed: {failed_count:,}\n"
            f"Success rate: {success_rate:.1f}%",
            parse_mode=ParseMode.HTML
        )
        
        log_user_action(
            session['admin_id'], 
            "BROADCAST_SENT", 
            f"Sent: {sent_count}, Blocked: {blocked_count}, Failed: {failed_count}"
        )
        
    except Exception as e:
        error_msg = html.escape(str(e))
        await callback.message.edit_text(f"Broadcast failed: {error_msg}")
        logger.error(f"Broadcast failed: {e}")

@router.message(Command("users"))
async def cmd_users(message: types.Message):
    """User management commands"""
    if not Config.is_admin(message.from_user.id):
        await message.reply("This command is only available for administrators.")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    try:
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
            
            activity_rate = (active_users / total_users * 100) if total_users > 0 else 0
            
            user_stats = (
                f"<b>User Management</b>\n\n"
                f"<b>Overview:</b>\n"
                f"• Total users: {total_users:,}\n"
                f"• Active (7d): {active_users:,}\n"
                f"• Activity rate: {activity_rate:.1f}%\n\n"
                f"<b>Growth:</b>\n"
                f"• Today: +{today_users:,}\n"
                f"• This week: +{week_users:,}\n"
                f"• This month: +{month_users:,}\n\n"
                f"<b>Commands:</b>\n"
                f"• <code>/users find &lt;user_id&gt;</code> - Find user info\n"
                f"• <code>/users recent</code> - Show recent users\n"
                f"• <code>/users active</code> - Show active users"
            )
            
            await message.reply(user_stats, parse_mode=ParseMode.HTML)
        
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
                    
                    username = html.escape(user.get('username', 'N/A'))
                    first_name = html.escape(user.get('first_name', 'N/A'))
                    connected_chat = html.escape(str(user.get('connected_chat', 'None')))
                    
                    user_info = (
                        f"<b>User Information</b>\n\n"
                        f"<b>ID:</b> <code>{user['user_id']}</code>\n"
                        f"<b>Username:</b> @{username}\n"
                        f"<b>First Name:</b> {first_name}\n"
                        f"<b>Joined:</b> {joined}\n"
                        f"<b>Last Activity:</b> {last_activity}\n"
                        f"<b>Connected Chat:</b> {connected_chat}"
                    )
                    
                    await message.reply(user_info, parse_mode=ParseMode.HTML)
                else:
                    await message.reply(f"User with ID <code>{user_id}</code> not found.", parse_mode=ParseMode.HTML)
                    
            except ValueError:
                await message.reply("Invalid user ID. Please provide a numeric user ID.")
        
        elif args[0] == "recent":
            # Show recent users
            recent_users = db.users.find({}).sort("joined_date", -1).limit(10)
            
            users_text = "<b>Recent Users (Last 10):</b>\n\n"
            async for user in recent_users:
                joined = user.get('joined_date', datetime.now())
                if isinstance(joined, datetime):
                    joined = joined.strftime('%m-%d %H:%M')
                
                username = html.escape(f"@{user.get('username', 'N/A')}")
                users_text += f"• {user['user_id']} | {username} | {joined}\n"
            
            await message.reply(users_text, parse_mode=ParseMode.HTML)
        
        elif args[0] == "active":
            # Show active users
            week_ago = datetime.now() - timedelta(days=7)
            active_users = db.users.find({
                "last_activity": {"$gte": week_ago}
            }).sort("last_activity", -1).limit(10)
            
            users_text = "<b>Active Users (Last 10):</b>\n\n"
            async for user in active_users:
                last_activity = user.get('last_activity', datetime.now())
                if isinstance(last_activity, datetime):
                    last_activity = last_activity.strftime('%m-%d %H:%M')
                
                username = html.escape(f"@{user.get('username', 'N/A')}")
                users_text += f"• {user['user_id']} | {username} | {last_activity}\n"
            
            await message.reply(users_text, parse_mode=ParseMode.HTML)
        
        else:
            await message.reply(
                "<b>User Commands:</b>\n"
                "• <code>/users stats</code> - User statistics\n"
                "• <code>/users find &lt;user_id&gt;</code> - Find user info\n"
                "• <code>/users recent</code> - Show recent users\n"
                "• <code>/users active</code> - Show active users",
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        error_msg = html.escape(str(e))
        await message.reply(f"User command error: {error_msg}")
        logger.error(f"User command error: {e}")

@router.message(Command("system"))
async def cmd_system(message: types.Message):
    """Show system information"""
    if not Config.is_admin(message.from_user.id):
        await message.reply("This command is only available for administrators.")
        return
    
    try:
        import psutil
        import platform
        
        # System info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database info
        db_name = html.escape(str(getattr(Config, 'DATABASE_NAME', 'Unknown')))
        log_level = html.escape(str(getattr(Config, 'LOG_LEVEL', 'Unknown')))
        max_channels = html.escape(str(getattr(Config, 'MAX_CHANNELS_PER_USER', 'Unknown')))
        backup_enabled = getattr(Config, 'ENABLE_BACKUP', False)
        analytics_enabled = getattr(Config, 'ENABLE_ANALYTICS', False)
        
        system_info = (
            f"<b>System Information</b>\n\n"
            f"<b>Platform:</b>\n"
            f"• OS: {platform.system()} {platform.release()}\n"
            f"• Python: {platform.python_version()}\n"
            f"• Architecture: {platform.machine()}\n\n"
            f"<b>Resources:</b>\n"
            f"• CPU Usage: {cpu_percent}%\n"
            f"• RAM Usage: {memory.percent}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)\n"
            f"• Disk Usage: {disk.percent}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)\n\n"
            f"<b>Configuration:</b>\n"
            f"• Database: {db_name}\n"
            f"• Log Level: {log_level}\n"
            f"• Max Channels/User: {max_channels}\n"
            f"• Backup Enabled: {'' if backup_enabled else ''}\n"
            f"• Analytics Enabled: {'' if analytics_enabled else ''}"
        )
        
        await message.reply(system_info, parse_mode=ParseMode.HTML)
        log_user_action(message.from_user.id, "SYSTEM_INFO_ACCESS")
        
    except ImportError:
        await message.reply("System monitoring not available (psutil not installed)")
    except Exception as e:
        error_msg = html.escape(str(e))
        await message.reply(f"System info error: {error_msg}")
        logger.error(f"System info error: {e}")

# Clean up expired broadcast sessions periodically
async def cleanup_broadcast_sessions():
    """Clean up expired broadcast sessions"""
    current_time = datetime.now()
    expired_sessions = [
        session_id for session_id, session in broadcast_sessions.items()
        if (current_time - session['created_at']).seconds > 300  # 5 minutes
    ]
    
    for session_id in expired_sessions:
        del broadcast_sessions[session_id]
