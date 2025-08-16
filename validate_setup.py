#!/usr/bin/env python3
"""
Quick validation script to test database setup components
"""

import asyncio
import sys
from database import migration_manager

async def validate_migration_manager():
    """Test that migration manager can read migration files"""
    try:
        # Test getting migration files
        migrations = migration_manager.get_migration_files()
        print(f"Found {len(migrations)} migration files:")
        
        for migration in migrations:
            print(f"  - {migration['version']}: {migration['filename']}")
        
        if not migrations:
            print("ERROR: No migration files found")
            return False
        
        # Check that initial migration exists
        initial_migration = next((m for m in migrations if m['version'] == '001'), None)
        if not initial_migration:
            print("ERROR: Initial migration (001) not found")
            return False
        
        print("✓ Migration files validation passed")
        return True
        
    except Exception as e:
        print(f"ERROR: Migration validation failed: {e}")
        return False

async def main():
    print("Validating database setup components...")
    print("-" * 40)
    
    success = await validate_migration_manager()
    
    if success:
        print("\n✓ All validations passed!")
        print("Database setup components are ready.")
        sys.exit(0)
    else:
        print("\n✗ Validation failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())