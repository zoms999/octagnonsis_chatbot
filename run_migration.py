"""
Simple script to run database migrations
"""

import asyncio
from database.migration_manager import migration_manager

async def main():
    print("Running database migrations...")
    success = await migration_manager.migrate()
    if success:
        print("Migrations completed successfully!")
    else:
        print("Migration failed!")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)