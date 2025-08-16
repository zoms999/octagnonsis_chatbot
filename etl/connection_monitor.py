#!/usr/bin/env python3
"""
ETL Connection Monitor
Monitors database connections during ETL processing
"""

import asyncio
import logging
from typing import Dict, Any
from sqlalchemy import text

logger = logging.getLogger(__name__)

class ETLConnectionMonitor:
    """Monitor database connections during ETL processing"""
    
    def __init__(self):
        self.initial_connections = 0
        self.peak_connections = 0
    
    async def start_monitoring(self):
        """Start connection monitoring"""
        from database.connection import db_manager
        
        async with db_manager.get_async_session() as session:
            result = await session.execute(text("""
                SELECT count(*) FROM pg_stat_activity 
                WHERE datname = current_database()
            """))
            self.initial_connections = result.scalar()
            self.peak_connections = self.initial_connections
            
        logger.info(f"Connection monitoring started. Initial connections: {self.initial_connections}")
    
    async def check_connections(self, stage_name: str = ""):
        """Check current connection count"""
        from database.connection import db_manager
        
        try:
            async with db_manager.get_async_session() as session:
                result = await session.execute(text("""
                    SELECT count(*) as total,
                           count(*) FILTER (WHERE state = 'active') as active,
                           count(*) FILTER (WHERE state = 'idle') as idle
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """))
                row = result.fetchone()
                total, active, idle = row[0], row[1], row[2]
                
                if total > self.peak_connections:
                    self.peak_connections = total
                
                stage_info = f" ({stage_name})" if stage_name else ""
                logger.info(f"Connections{stage_info}: Total={total}, Active={active}, Idle={idle}")
                
                return {"total": total, "active": active, "idle": idle}
                
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return {"total": 0, "active": 0, "idle": 0}
    
    async def end_monitoring(self):
        """End connection monitoring and report"""
        final_stats = await self.check_connections("final")
        
        logger.info(f"Connection monitoring ended.")
        logger.info(f"Initial connections: {self.initial_connections}")
        logger.info(f"Peak connections: {self.peak_connections}")
        logger.info(f"Final connections: {final_stats['total']}")
        
        if final_stats['total'] > self.initial_connections:
            logger.warning(f"Connection leak detected: {final_stats['total'] - self.initial_connections} connections not cleaned up")
        else:
            logger.info("No connection leak detected")

# Global monitor instance
connection_monitor = ETLConnectionMonitor()
