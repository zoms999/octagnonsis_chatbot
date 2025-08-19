"""
Initialization module for preference query optimization
Sets up the global optimizer instance and database indexes
"""

import logging
import asyncio
from typing import Optional, Dict, Any

from database.connection import db_manager
from etl.preference_query_optimizer import initialize_preference_query_optimizer, close_preference_query_optimizer
from database.preference_index_recommendations import analyze_and_recommend_indexes, create_preference_indexes
import structlog

logger = logging.getLogger(__name__)
init_logger = structlog.get_logger("preference_optimization_init")

async def initialize_preference_optimization(
    enable_optimizer: bool = True,
    create_indexes: bool = False,
    optimizer_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Initialize preference query optimization features
    
    Args:
        enable_optimizer: Whether to enable the query optimizer
        create_indexes: Whether to create recommended database indexes
        optimizer_config: Configuration for the optimizer
    
    Returns:
        Dictionary with initialization results
    """
    results = {
        "optimizer_initialized": False,
        "indexes_analyzed": False,
        "indexes_created": 0,
        "errors": []
    }
    
    init_logger.info(
        "Starting preference optimization initialization",
        enable_optimizer=enable_optimizer,
        create_indexes=create_indexes
    )
    
    try:
        # Initialize query optimizer if enabled
        if enable_optimizer:
            await _initialize_query_optimizer(optimizer_config, results)
        
        # Analyze and optionally create database indexes
        if create_indexes:
            await _initialize_database_indexes(results)
        else:
            # Just analyze indexes without creating them
            await _analyze_database_indexes(results)
        
        init_logger.info(
            "Preference optimization initialization completed",
            results=results
        )
        
    except Exception as e:
        error_msg = f"Failed to initialize preference optimization: {str(e)}"
        results["errors"].append(error_msg)
        init_logger.error(
            "Preference optimization initialization failed",
            error=str(e)
        )
    
    return results

async def _initialize_query_optimizer(
    config: Optional[Dict[str, Any]], 
    results: Dict[str, Any]
) -> None:
    """Initialize the preference query optimizer"""
    try:
        # Get database configuration
        db_config = db_manager.config
        
        # Default optimizer configuration
        default_config = {
            "pool_size": 20,
            "max_overflow": 30,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "query_timeout": 30,
            "cache_ttl": 300,
            "enable_cache": True
        }
        
        # Merge with provided config
        if config:
            default_config.update(config)
        
        # Initialize the global optimizer
        optimizer = initialize_preference_query_optimizer(
            connection_string=db_config.sync_url,
            **default_config
        )
        
        results["optimizer_initialized"] = True
        
        init_logger.info(
            "Preference query optimizer initialized",
            config=default_config
        )
        
    except Exception as e:
        error_msg = f"Failed to initialize query optimizer: {str(e)}"
        results["errors"].append(error_msg)
        init_logger.error(
            "Query optimizer initialization failed",
            error=str(e)
        )

async def _analyze_database_indexes(results: Dict[str, Any]) -> None:
    """Analyze database indexes and provide recommendations"""
    try:
        recommendations = await analyze_and_recommend_indexes()
        
        results["indexes_analyzed"] = True
        results["index_recommendations"] = len(recommendations)
        
        # Log recommendations summary
        high_priority = len([r for r in recommendations if r.priority == "high"])
        medium_priority = len([r for r in recommendations if r.priority == "medium"])
        low_priority = len([r for r in recommendations if r.priority == "low"])
        
        init_logger.info(
            "Database index analysis completed",
            total_recommendations=len(recommendations),
            high_priority=high_priority,
            medium_priority=medium_priority,
            low_priority=low_priority
        )
        
        # Log specific high-priority recommendations
        for rec in recommendations:
            if rec.priority == "high":
                init_logger.info(
                    "High priority index recommendation",
                    index_name=rec.index_name,
                    table_name=rec.table_name,
                    columns=rec.columns,
                    rationale=rec.rationale
                )
        
    except Exception as e:
        error_msg = f"Failed to analyze database indexes: {str(e)}"
        results["errors"].append(error_msg)
        init_logger.error(
            "Database index analysis failed",
            error=str(e)
        )

async def _initialize_database_indexes(results: Dict[str, Any]) -> None:
    """Create recommended database indexes"""
    try:
        # First analyze what indexes are needed
        await _analyze_database_indexes(results)
        
        # Create the indexes (not in dry run mode)
        creation_results = await create_preference_indexes(dry_run=False)
        
        results["indexes_created"] = len(creation_results["created"])
        results["indexes_failed"] = len(creation_results["failed"])
        results["indexes_skipped"] = len(creation_results["skipped"])
        
        init_logger.info(
            "Database index creation completed",
            created=results["indexes_created"],
            failed=results["indexes_failed"],
            skipped=results["indexes_skipped"]
        )
        
        # Log any failures
        for failed in creation_results["failed"]:
            init_logger.error(
                "Failed to create index",
                index_name=failed["index_name"],
                table_name=failed["table_name"],
                error=failed["error"]
            )
        
    except Exception as e:
        error_msg = f"Failed to create database indexes: {str(e)}"
        results["errors"].append(error_msg)
        init_logger.error(
            "Database index creation failed",
            error=str(e)
        )

async def cleanup_preference_optimization() -> None:
    """Cleanup preference optimization resources"""
    init_logger.info("Cleaning up preference optimization resources")
    
    try:
        await close_preference_query_optimizer()
        init_logger.info("Preference optimization cleanup completed")
    except Exception as e:
        init_logger.error(
            "Failed to cleanup preference optimization",
            error=str(e)
        )

def get_optimization_status() -> Dict[str, Any]:
    """Get current status of preference optimization features"""
    from etl.preference_query_optimizer import get_preference_query_optimizer
    
    optimizer = get_preference_query_optimizer()
    
    status = {
        "optimizer_enabled": optimizer is not None,
        "timestamp": None,
        "performance_metrics": None,
        "connection_pool_metrics": None,
        "cache_stats": None
    }
    
    if optimizer:
        try:
            status["performance_metrics"] = optimizer.get_performance_metrics()
            status["connection_pool_metrics"] = optimizer.get_connection_pool_metrics()
            status["cache_stats"] = optimizer.get_cache_stats()
            status["timestamp"] = optimizer.generate_performance_report()["timestamp"]
        except Exception as e:
            status["error"] = str(e)
    
    return status

# Convenience functions for common initialization patterns

async def initialize_for_development() -> Dict[str, Any]:
    """Initialize optimization for development environment"""
    return await initialize_preference_optimization(
        enable_optimizer=True,
        create_indexes=False,  # Don't create indexes in development
        optimizer_config={
            "pool_size": 5,
            "max_overflow": 10,
            "query_timeout": 15,
            "cache_ttl": 60,  # Shorter cache for development
            "enable_cache": True
        }
    )

async def initialize_for_production() -> Dict[str, Any]:
    """Initialize optimization for production environment"""
    return await initialize_preference_optimization(
        enable_optimizer=True,
        create_indexes=True,  # Create indexes in production
        optimizer_config={
            "pool_size": 20,
            "max_overflow": 30,
            "query_timeout": 30,
            "cache_ttl": 300,
            "enable_cache": True
        }
    )

async def initialize_for_testing() -> Dict[str, Any]:
    """Initialize optimization for testing environment"""
    return await initialize_preference_optimization(
        enable_optimizer=True,
        create_indexes=False,  # Don't create indexes in testing
        optimizer_config={
            "pool_size": 3,
            "max_overflow": 5,
            "query_timeout": 10,
            "cache_ttl": 30,  # Very short cache for testing
            "enable_cache": False  # Disable cache for consistent testing
        }
    )