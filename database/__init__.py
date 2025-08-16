"""
Database package for Aptitude Chatbot RAG System
Provides database connection, models, and migration management
"""

from .connection import (
    DatabaseConfig,
    DatabaseManager,
    db_manager,
    get_async_session,
    get_sync_session,
    Base
)

from .models import (
    ChatUser,
    ChatDocument,
    ChatJob,
    ChatMajor,
    ChatConversation,
    DocumentType
)

from .migration_manager import (
    MigrationManager,
    migration_manager,
    run_migrations,
    get_migration_status
)

__all__ = [
    # Connection utilities
    'DatabaseConfig',
    'DatabaseManager', 
    'db_manager',
    'get_async_session',
    'get_sync_session',
    'Base',
    
    # Models
    'ChatUser',
    'ChatDocument', 
    'ChatJob',
    'ChatMajor',
    'ChatConversation',
    'DocumentType',
    
    # Migration management
    'MigrationManager',
    'migration_manager',
    'run_migrations',
    'get_migration_status'
]