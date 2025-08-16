"""
Database migration management for Aptitude Chatbot RAG System
Handles schema migrations, version tracking, and rollback capabilities
"""

import os
import logging
import asyncio
from typing import List, Dict, Optional
from pathlib import Path
from sqlalchemy import text, MetaData
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import DatabaseManager, db_manager

logger = logging.getLogger(__name__)

class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self, db_manager: DatabaseManager, migrations_dir: str = "database/migrations"):
        self.db_manager = db_manager
        self.migrations_dir = Path(migrations_dir)
        self.migrations_table = "schema_migrations"
    
    async def initialize_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        async with self.db_manager.get_async_session() as session:
            await session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                    version VARCHAR(255) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum VARCHAR(64)
                )
            """))
            await session.commit()
            logger.info(f"Initialized {self.migrations_table} table")
    
    def get_migration_files(self) -> List[Dict[str, str]]:
        """Get all migration files sorted by version"""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory {self.migrations_dir} does not exist")
            return []
        
        migrations = []
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            # Extract version from filename (e.g., "001_initial_schema.sql" -> "001")
            version = file_path.stem.split('_')[0]
            migrations.append({
                'version': version,
                'filename': file_path.name,
                'filepath': str(file_path)
            })
        
        return migrations
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        try:
            async with self.db_manager.get_async_session() as session:
                result = await session.execute(
                    text(f"SELECT version FROM {self.migrations_table} ORDER BY version")
                )
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.warning(f"Could not fetch applied migrations: {e}")
            return []
    
    async def apply_migration(self, migration: Dict[str, str]) -> bool:
        """Apply a single migration"""
        try:
            # Read migration file
            with open(migration['filepath'], 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Split SQL content into individual statements
            statements = self._split_sql_statements(sql_content)
            
            async with self.db_manager.get_async_session() as session:
                # Execute each statement separately
                for statement in statements:
                    if statement.strip():
                        await session.execute(text(statement))
                
                # Record migration as applied
                await session.execute(text(f"""
                    INSERT INTO {self.migrations_table} (version, filename)
                    VALUES (:version, :filename)
                """), {
                    'version': migration['version'],
                    'filename': migration['filename']
                })
                
                await session.commit()
                logger.info(f"Applied migration {migration['version']}: {migration['filename']}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to apply migration {migration['version']}: {e}")
            return False
    
    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements"""
        # Remove comments and split by semicolons
        lines = []
        for line in sql_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        content = ' '.join(lines)
        
        # Split by semicolons, but handle function definitions with $$ delimiters
        statements = []
        current_statement = ""
        in_function = False
        
        parts = content.split(';')
        for part in parts:
            current_statement += part
            
            # Check for function definition markers
            if '$$' in part:
                dollar_count = part.count('$$')
                if dollar_count % 2 == 1:  # Odd number means we're entering/exiting function
                    in_function = not in_function
            
            if not in_function and current_statement.strip():
                statements.append(current_statement.strip() + ';')
                current_statement = ""
            elif in_function:
                current_statement += ';'
        
        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return [s for s in statements if s.strip()]
    
    async def migrate(self) -> bool:
        """Run all pending migrations"""
        try:
            await self.initialize_migrations_table()
            
            all_migrations = self.get_migration_files()
            applied_migrations = await self.get_applied_migrations()
            
            pending_migrations = [
                m for m in all_migrations 
                if m['version'] not in applied_migrations
            ]
            
            if not pending_migrations:
                logger.info("No pending migrations")
                return True
            
            logger.info(f"Found {len(pending_migrations)} pending migrations")
            
            for migration in pending_migrations:
                success = await self.apply_migration(migration)
                if not success:
                    logger.error(f"Migration failed at {migration['version']}")
                    return False
            
            logger.info("All migrations applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            return False
    
    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration (if rollback script exists)"""
        rollback_file = self.migrations_dir / f"{version}_rollback.sql"
        
        if not rollback_file.exists():
            logger.error(f"No rollback script found for migration {version}")
            return False
        
        try:
            with open(rollback_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            async with self.db_manager.get_async_session() as session:
                # Execute rollback SQL
                await session.execute(text(sql_content))
                
                # Remove migration record
                await session.execute(text(f"""
                    DELETE FROM {self.migrations_table} WHERE version = :version
                """), {'version': version})
                
                await session.commit()
                logger.info(f"Rolled back migration {version}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to rollback migration {version}: {e}")
            return False
    
    async def get_migration_status(self) -> Dict[str, any]:
        """Get current migration status"""
        all_migrations = self.get_migration_files()
        applied_migrations = await self.get_applied_migrations()
        
        pending = [m for m in all_migrations if m['version'] not in applied_migrations]
        
        return {
            'total_migrations': len(all_migrations),
            'applied_count': len(applied_migrations),
            'pending_count': len(pending),
            'applied_versions': applied_migrations,
            'pending_migrations': [m['version'] for m in pending]
        }

# Global migration manager instance
migration_manager = MigrationManager(db_manager)

async def run_migrations():
    """Convenience function to run migrations"""
    return await migration_manager.migrate()

async def get_migration_status():
    """Convenience function to get migration status"""
    return await migration_manager.get_migration_status()

if __name__ == "__main__":
    # CLI interface for running migrations
    import sys
    
    async def main():
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "migrate":
                success = await run_migrations()
                sys.exit(0 if success else 1)
            
            elif command == "status":
                status = await get_migration_status()
                print(f"Migration Status:")
                print(f"  Total migrations: {status['total_migrations']}")
                print(f"  Applied: {status['applied_count']}")
                print(f"  Pending: {status['pending_count']}")
                if status['pending_migrations']:
                    print(f"  Pending versions: {', '.join(status['pending_migrations'])}")
            
            elif command == "rollback" and len(sys.argv) > 2:
                version = sys.argv[2]
                success = await migration_manager.rollback_migration(version)
                sys.exit(0 if success else 1)
            
            else:
                print("Usage: python migration_manager.py [migrate|status|rollback <version>]")
                sys.exit(1)
        else:
            print("Usage: python migration_manager.py [migrate|status|rollback <version>]")
            sys.exit(1)
    
    asyncio.run(main())