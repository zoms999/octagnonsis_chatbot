"""
Database connection utilities for Aptitude Chatbot RAG System
Provides connection management, session handling, and configuration
"""

import os
import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, environment variables should be set externally
    pass

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
Base = declarative_base()

class DatabaseConfig:
    """Database configuration management"""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '5432'))
        self.database = os.getenv('DB_NAME')
        self.username = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '10'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '20'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
    
    @property
    def sync_url(self) -> str:
        """Synchronous database URL"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def async_url(self) -> str:
        """Asynchronous database URL"""
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._async_engine = None
        self._sync_engine = None
        self._async_session_factory = None
        self._sync_session_factory = None
    
    def get_sync_engine(self):
        """Get synchronous database engine"""
        if self._sync_engine is None:
            self._sync_engine = create_engine(
                self.config.sync_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=os.getenv('DB_ECHO', 'false').lower() == 'true'
            )
        return self._sync_engine
    
    def get_async_engine(self):
        """Get asynchronous database engine"""
        if self._async_engine is None:
            self._async_engine = create_async_engine(
                self.config.async_url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
                pool_pre_ping=True  # detect stale connections
            )
        return self._async_engine
    
    def get_sync_session_factory(self):
        """Get synchronous session factory"""
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.get_sync_engine(),
                autocommit=False,
                autoflush=False
            )
        return self._sync_session_factory
    
    def get_async_session_factory(self):
        """Get asynchronous session factory"""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.get_async_engine(),
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._async_session_factory
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with automatic cleanup"""
        session_factory = self.get_async_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()
    
    def get_sync_session(self):
        """Get synchronous database session"""
        session_factory = self.get_sync_session_factory()
        return session_factory()
    
    async def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def check_pgvector_extension(self) -> bool:
        """Check if pgvector extension is installed"""
        try:
            async with self.get_async_session() as session:
                result = await session.execute(
                    text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                )
                return result.scalar()
        except Exception as e:
            logger.error(f"pgvector extension check failed: {e}")
            return False
    
    async def close(self):
        """Close database connections"""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._sync_engine:
            self._sync_engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for getting sessions
async def get_async_session() -> AsyncSession:
    """Get async database session"""
    session_factory = db_manager.get_async_session_factory()
    return session_factory()

def get_sync_session():
    """Get sync database session"""
    return db_manager.get_sync_session()

async def init_database() -> bool:
    """Initialize database on app startup.
    Ensures engines are created and runs pending migrations.
    Returns True on success, False on failure.
    """
    try:
        # Ensure engines are initialized
        _ = db_manager.get_async_engine()
        _ = db_manager.get_sync_engine()

        # Run migrations (creates tables/extensions if needed)
        try:
            from database.migration_manager import run_migrations
            success = await run_migrations()
            if not success:
                logger.error("Database migrations failed")
                return False
        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            return False

        # Optional: quick connectivity test
        ok = await db_manager.test_connection()
        if not ok:
            logger.error("Database connectivity test failed after initialization")
            return False

        logger.info("Database initialized (migrations applied, connectivity verified)")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False