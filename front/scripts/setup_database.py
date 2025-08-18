#!/usr/bin/env python3
"""
Database setup script for Aptitude Chatbot RAG System
Initializes database, runs migrations, and verifies setup
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import db_manager, migration_manager
from database.connection import DatabaseConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_database_connection():
    """Test database connectivity"""
    logger.info("Testing database connection...")
    
    try:
        connected = await db_manager.test_connection()
        if connected:
            logger.info("✓ Database connection successful")
            return True
        else:
            logger.error("✗ Database connection failed")
            return False
    except Exception as e:
        logger.error(f"✗ Database connection error: {e}")
        return False

async def check_pgvector_extension():
    """Verify pgvector extension is available"""
    logger.info("Checking pgvector extension...")
    
    try:
        has_pgvector = await db_manager.check_pgvector_extension()
        if has_pgvector:
            logger.info("✓ pgvector extension is installed")
            return True
        else:
            logger.error("✗ pgvector extension is not installed")
            logger.error("Please install pgvector extension in your PostgreSQL database")
            logger.error("Run: CREATE EXTENSION IF NOT EXISTS vector;")
            return False
    except Exception as e:
        logger.error(f"✗ pgvector extension check failed: {e}")
        return False

async def run_database_migrations():
    """Execute database migrations"""
    logger.info("Running database migrations...")
    
    try:
        success = await migration_manager.migrate()
        if success:
            logger.info("✓ Database migrations completed successfully")
            return True
        else:
            logger.error("✗ Database migrations failed")
            return False
    except Exception as e:
        logger.error(f"✗ Migration error: {e}")
        return False

async def verify_schema():
    """Verify that all required tables exist"""
    logger.info("Verifying database schema...")
    
    required_tables = [
        'chat_users',
        'chat_documents', 
        'chat_jobs',
        'chat_majors',
        'chat_conversations',
        'schema_migrations'
    ]
    
    try:
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            
            for table in required_tables:
                result = await session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """))
                
                exists = result.scalar()
                if exists:
                    logger.info(f"✓ Table '{table}' exists")
                else:
                    logger.error(f"✗ Table '{table}' missing")
                    return False
            
            logger.info("✓ All required tables exist")
            return True
            
    except Exception as e:
        logger.error(f"✗ Schema verification failed: {e}")
        return False

async def show_migration_status():
    """Display current migration status"""
    logger.info("Checking migration status...")
    
    try:
        status = await migration_manager.get_migration_status()
        
        logger.info(f"Migration Status:")
        logger.info(f"  Total migrations: {status['total_migrations']}")
        logger.info(f"  Applied: {status['applied_count']}")
        logger.info(f"  Pending: {status['pending_count']}")
        
        if status['applied_versions']:
            logger.info(f"  Applied versions: {', '.join(status['applied_versions'])}")
        
        if status['pending_migrations']:
            logger.info(f"  Pending versions: {', '.join(status['pending_migrations'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to get migration status: {e}")
        return False

async def main():
    """Main setup function"""
    logger.info("Starting database setup for Aptitude Chatbot RAG System")
    logger.info("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Display configuration
    config = DatabaseConfig()
    logger.info(f"Database: {config.database}")
    logger.info(f"Host: {config.host}:{config.port}")
    logger.info(f"User: {config.username}")
    logger.info("-" * 60)
    
    # Run setup steps
    steps = [
        ("Database Connection", check_database_connection),
        ("pgvector Extension", check_pgvector_extension),
        ("Database Migrations", run_database_migrations),
        ("Schema Verification", verify_schema),
        ("Migration Status", show_migration_status)
    ]
    
    all_success = True
    
    for step_name, step_func in steps:
        logger.info(f"\n[{step_name}]")
        success = await step_func()
        if not success:
            all_success = False
            logger.error(f"Setup failed at step: {step_name}")
            break
    
    # Cleanup
    await db_manager.close()
    
    if all_success:
        logger.info("\n" + "=" * 60)
        logger.info("✓ Database setup completed successfully!")
        logger.info("The Aptitude Chatbot RAG System database is ready to use.")
        sys.exit(0)
    else:
        logger.error("\n" + "=" * 60)
        logger.error("✗ Database setup failed!")
        logger.error("Please check the errors above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())