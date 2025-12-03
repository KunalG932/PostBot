"""
Backup utility for PostBot
Automated database backup and restore functionality
"""
import asyncio
import json
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
from utils.logger import logger, log_system_event, log_error

class BackupManager:
    """Database backup and restore manager"""
    
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.client = None
        self.db = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(Config.get_db_uri())
            self.db = self.client[Config.DATABASE_NAME]
            log_system_event("BackupManager connected to database")
        except Exception as e:
            log_error(e, "BackupManager database connection failed")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            log_system_event("BackupManager disconnected from database")
    
    async def create_backup(self, compress: bool = True) -> str:
        """Create a full database backup
        
        Args:
            compress: Whether to compress the backup file
            
        Returns:
            Path to the created backup file
        """
        if not self.client:
            await self.connect()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"postbot_backup_{timestamp}"
        backup_file = self.backup_dir / f"{backup_name}.json"
        
        try:
            # Get all collections
            collections = await self.db.list_collection_names()
            backup_data = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "database": Config.DATABASE_NAME,
                    "collections": collections,
                    "version": "2.0.0"
                },
                "data": {}
            }
            
            # Backup each collection
            for collection_name in collections:
                collection = self.db[collection_name]
                documents = []
                
                async for doc in collection.find():
                    # Convert ObjectId to string for JSON serialization
                    if '_id' in doc:
                        doc['_id'] = str(doc['_id'])
                    # Handle datetime objects
                    for key, value in doc.items():
                        if isinstance(value, datetime):
                            doc[key] = value.isoformat()
                    documents.append(doc)
                
                backup_data["data"][collection_name] = documents
                log_system_event(f"Backed up collection: {collection_name}", f"{len(documents)} documents")
            
            # Write backup file
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            # Compress if requested
            if compress:
                compressed_file = backup_file.with_suffix('.json.gz')
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_file.unlink()  # Remove uncompressed file
                backup_file = compressed_file
            
            file_size = backup_file.stat().st_size / (1024 * 1024)  # MB
            log_system_event(
                "Backup created successfully",
                f"File: {backup_file.name}, Size: {file_size:.2f}MB, Collections: {len(collections)}"
            )
            
            return str(backup_file)
            
        except Exception as e:
            log_error(e, "Backup creation failed")
            raise
    
    async def restore_backup(self, backup_file: str, drop_existing: bool = False) -> bool:
        """Restore database from backup file
        
        Args:
            backup_file: Path to backup file
            drop_existing: Whether to drop existing collections before restore
            
        Returns:
            True if restore was successful
        """
        if not self.client:
            await self.connect()
        
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        try:
            # Read backup file
            if backup_path.suffix == '.gz':
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            
            log_system_event("Starting database restore", f"From: {backup_path.name}")
            
            # Validate backup format
            if "metadata" not in backup_data or "data" not in backup_data:
                raise ValueError("Invalid backup format")
            
            metadata = backup_data["metadata"]
            log_system_event(
                "Backup metadata",
                f"Created: {metadata.get('created_at')}, Collections: {len(metadata.get('collections', []))}"
            )
            
            # Restore each collection
            for collection_name, documents in backup_data["data"].items():
                collection = self.db[collection_name]
                
                if drop_existing:
                    await collection.drop()
                    log_system_event(f"Dropped existing collection: {collection_name}")
                
                if documents:
                    # Convert string IDs back to ObjectId and handle dates
                    from bson import ObjectId
                    from dateutil import parser
                    
                    for doc in documents:
                        if '_id' in doc and isinstance(doc['_id'], str):
                            try:
                                doc['_id'] = ObjectId(doc['_id'])
                            except:
                                # If not a valid ObjectId, let MongoDB generate a new one
                                del doc['_id']
                        
                        # Convert date strings back to datetime
                        for key, value in doc.items():
                            if isinstance(value, str) and key.endswith('_date'):
                                try:
                                    doc[key] = parser.parse(value)
                                except:
                                    pass
                    
                    await collection.insert_many(documents, ordered=False)
                
                log_system_event(f"Restored collection: {collection_name}", f"{len(documents)} documents")
            
            log_system_event("Database restore completed successfully")
            return True
            
        except Exception as e:
            log_error(e, "Database restore failed")
            raise
    
    async def list_backups(self) -> List[Dict]:
        """List all available backups
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        for backup_file in self.backup_dir.glob("postbot_backup_*.json*"):
            try:
                file_size = backup_file.stat().st_size / (1024 * 1024)  # MB
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                # Try to read metadata
                metadata = None
                try:
                    if backup_file.suffix == '.gz':
                        with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                            data = json.load(f)
                    else:
                        with open(backup_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    metadata = data.get("metadata", {})
                except:
                    pass
                
                backup_info = {
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size_mb": round(file_size, 2),
                    "created_at": file_time.isoformat(),
                    "compressed": backup_file.suffix == '.gz',
                    "metadata": metadata
                }
                
                backups.append(backup_info)
                
            except Exception as e:
                log_error(e, f"Error reading backup info: {backup_file}")
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
    
    async def cleanup_old_backups(self, retention_days: int = None) -> int:
        """Clean up old backup files
        
        Args:
            retention_days: Number of days to keep backups (uses config default if None)
            
        Returns:
            Number of files deleted
        """
        if retention_days is None:
            retention_days = Config.BACKUP_RETENTION
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        
        for backup_file in self.backup_dir.glob("postbot_backup_*.json*"):
            try:
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
                    log_system_event(f"Deleted old backup: {backup_file.name}")
            except Exception as e:
                log_error(e, f"Error deleting backup: {backup_file}")
        
        if deleted_count > 0:
            log_system_event(f"Cleanup completed", f"Deleted {deleted_count} old backup files")
        
        return deleted_count
    
    async def get_backup_stats(self) -> Dict:
        """Get backup statistics
        
        Returns:
            Dictionary with backup statistics
        """
        backups = await self.list_backups()
        
        if not backups:
            return {
                "total_backups": 0,
                "total_size_mb": 0,
                "latest_backup": None,
                "oldest_backup": None
            }
        
        total_size = sum(backup["size_mb"] for backup in backups)
        latest = max(backups, key=lambda x: x["created_at"])
        oldest = min(backups, key=lambda x: x["created_at"])
        
        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size, 2),
            "latest_backup": latest["created_at"],
            "oldest_backup": oldest["created_at"]
        }

# Global backup manager instance
backup_manager = BackupManager()

# Scheduled backup task
async def scheduled_backup_task():
    """Background task for scheduled backups"""
    if not Config.ENABLE_BACKUP:
        return
    
    log_system_event("Starting scheduled backup task")
    
    while True:
        try:
            await asyncio.sleep(Config.BACKUP_INTERVAL)
            
            # Create backup
            backup_file = await backup_manager.create_backup(compress=True)
            log_system_event("Scheduled backup completed", f"File: {backup_file}")
            
            # Cleanup old backups
            deleted_count = await backup_manager.cleanup_old_backups()
            if deleted_count > 0:
                log_system_event("Old backups cleaned up", f"Deleted: {deleted_count}")
            
        except Exception as e:
            log_error(e, "Scheduled backup failed")
            await asyncio.sleep(300)  # Wait 5 minutes before retry
