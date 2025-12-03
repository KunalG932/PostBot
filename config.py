# PostBot - Telegram Channel Management Bot
# Environment Configuration

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Bot configuration class"""
    
    # Bot settings
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is required")
    
    # Database settings
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/postbot")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "postbot")
    
    # Optional settings
    CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
      # Developer info
    DEVELOPER_USERNAME = "DevIncognito"
    DEVELOPER_CHANNEL = "@lncognitobots"
    GITHUB_REPO = "https://github.com/KunalG932/PostBot"
    
    # Bot limits
    MAX_CHANNELS_PER_USER = int(os.getenv("MAX_CHANNELS_PER_USER", "10"))
    MAX_BUTTONS_PER_POST = int(os.getenv("MAX_BUTTONS_PER_POST", "10"))
    MAX_MEDIA_PER_POST = int(os.getenv("MAX_MEDIA_PER_POST", "10"))
    
    # Cache settings
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "postbot.log")
      # Admin settings
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
    
    # Feature flags
    ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
    ENABLE_BACKUP = os.getenv("ENABLE_BACKUP", "true").lower() == "true"
    ENABLE_NOTIFICATIONS = os.getenv("ENABLE_NOTIFICATIONS", "true").lower() == "true"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
    
    # Backup settings
    BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL", "86400"))  # 24 hours
    BACKUP_RETENTION = int(os.getenv("BACKUP_RETENTION", "7"))  # days
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        
        if not cls.MONGO_URI:
            raise ValueError("MONGO_URI is required")
        
        # Validate numeric settings
        if cls.MAX_CHANNELS_PER_USER <= 0:
            raise ValueError("MAX_CHANNELS_PER_USER must be positive")
        
        if cls.MAX_BUTTONS_PER_POST <= 0:
            raise ValueError("MAX_BUTTONS_PER_POST must be positive")
        
        if cls.CACHE_TTL < 0:
            raise ValueError("CACHE_TTL cannot be negative")
        
        return True
    
    @classmethod
    def get_db_uri(cls):
        """Get database URI with proper formatting"""
        return cls.MONGO_URI
    
    @classmethod
    def is_admin(cls, user_id):
        """Check if user is admin"""
        return user_id in cls.ADMIN_IDS
    
    @classmethod
    def get_feature_status(cls):
        """Get status of all features"""
        return {
            "analytics": cls.ENABLE_ANALYTICS,
            "backup": cls.ENABLE_BACKUP,
            "notifications": cls.ENABLE_NOTIFICATIONS
        }
        
        return True
