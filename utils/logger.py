"""
Logging utility for PostBot
Enhanced logging with file rotation and formatting
"""
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

from config import Config

class BotLogger:
    """Enhanced logger for PostBot"""
    
    def __init__(self, name: str = "postbot"):
        self.name = name
        self.logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with file and console handlers"""
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            filename=logs_dir / Config.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        
        # Formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            fmt='%(levelname)-8s | %(message)s'
        )
        
        # Set formatters
        file_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(simple_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_logger(self):
        """Get the configured logger"""
        return self.logger
    
    def log_user_action(self, user_id: int, action: str, details: str = ""):
        """Log user actions with standardized format"""
        message = f"User {user_id} | {action}"
        if details:
            message += f" | {details}"
        self.logger.info(message)
    
    def log_error(self, error: Exception, context: str = ""):
        """Log errors with context"""
        message = f"ERROR: {str(error)}"
        if context:
            message = f"{context} | {message}"
        self.logger.error(message, exc_info=True)
    
    def log_api_call(self, method: str, params: dict = None, success: bool = True):
        """Log API calls"""
        status = "SUCCESS" if success else "FAILED"
        message = f"API {method} | {status}"
        if params:
            message += f" | Params: {params}"
        self.logger.info(message)
    
    def log_database_operation(self, operation: str, collection: str, success: bool = True, count: int = None):
        """Log database operations"""
        status = "SUCCESS" if success else "FAILED"
        message = f"DB {operation} | {collection} | {status}"
        if count is not None:
            message += f" | Count: {count}"
        self.logger.info(message)
    
    def log_system_event(self, event: str, details: str = ""):
        """Log system events"""
        message = f"SYSTEM | {event}"
        if details:
            message += f" | {details}"
        self.logger.info(message)

# Global logger instance
logger = BotLogger().get_logger()

# Convenience functions
def log_user_action(user_id: int, action: str, details: str = ""):
    """Log user actions"""
    BotLogger().log_user_action(user_id, action, details)

def log_error(error: Exception, context: str = ""):
    """Log errors with context"""
    BotLogger().log_error(error, context)

def log_api_call(method: str, params: dict = None, success: bool = True):
    """Log API calls"""
    BotLogger().log_api_call(method, params, success)

def log_database_operation(operation: str, collection: str, success: bool = True, count: int = None):
    """Log database operations"""
    BotLogger().log_database_operation(operation, collection, success, count)

def log_system_event(event: str, details: str = ""):
    """Log system events"""
    BotLogger().log_system_event(event, details)

# Performance logging decorator
def log_performance(func_name: str):
    """Decorator to log function performance"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"PERFORMANCE | {func_name} | {duration:.3f}s | SUCCESS")
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(f"PERFORMANCE | {func_name} | {duration:.3f}s | ERROR: {str(e)}")
                raise
        return wrapper
    return decorator
