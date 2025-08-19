#!/usr/bin/env python3
"""
CLI tool for managing preference query optimization
Provides commands for initializing, monitoring, and managing preference query performance
"""

import asyncio
import argparse
import json
import sys
from typing import Dict, Any
from datetime import datetime

from etl.preference_optimization_init import (
    initialize_preference_optimization,
    cleanup_preference_optimization,
    get_optimization_status,
    initialize_for_development,
    initialize_for_production,
    initialize_for_testing
)
from etl.preference_query_optimizer import get_preference_query_optimizer
from database.preference_index_recommendations import (
    analyze_and_recommend_indexes,
    create_preference_indexes,
    PreferenceIndexAnalyzer
)
from database.connection import init_database

def print_json(data: Dict[str, Any]) -> None:
    """Print data as formatted JSON"""
    print(json.dumps(data, indent=2, default=str))

def print_status(message: str, success: bool = True) -> None:
    """Print status message with color coding"""
    prefix = "✓" if success else "✗"
    print(f"{prefix} {message}")

async def cmd_init(args) -> None:
    """Initialize preference query optimization"""
    print("Initializing preference query optimization...")
    
    # Initialize database first
    print("Initializing database connection...")
    db_success = await init_database()
    if not db_success:
        print_status("Failed to initialize database", False)
        sys.exit(1)
    print_status("Database initialized")
    
    # Choose initialization method based on environment
    if args.environment == "development":
        results = await initialize_for_development()
    elif args.environment == "production":
        results = await initialize_for_production()
    elif args.environment == "testing":
        results = await initialize_for_testing()
    else:
        # Custom initialization
        config = {}
        if args.pool_size:
            config["pool_size"] = args.pool_size
        if args.query_timeout:
            config["query_timeout"] = args.query_timeout
        if args.cache_ttl:
            config["cache_ttl"] = args.cache_ttl
        
        results = await initialize_preference_optimization(
            enable_optimizer=not args.disable_optimizer,
            create_indexes=args.create_indexes,
            optimizer_config=config if config else None
        )
    
    # Print results
    if results["errors"]:
        print_status("Initialization completed with errors", False)
        for error in results["errors"]:
            print(f"  Error: {error}")
    else:
        print_status("Initialization completed successfully")
    
    if args.verbose:
        print("\nInitialization Results:")
        print_json(results)

async def cmd_status(args) -> None:
    """Show optimization status"""
    print("Checking preference query optimization status...")
    
    status = get_optimization_status()
    
    print(f"\nOptimization Status (as of {datetime.now().isoformat()}):")
    print(f"Optimizer Enabled: {'Yes' if status['optimizer_enabled'] else 'No'}")
    
    if status["optimizer_enabled"]:
        optimizer = get_preference_query_optimizer()
        if optimizer:
            # Get detailed metrics
            performance_report = optimizer.generate_performance_report()
            
            print(f"\nPerformance Summary:")
            overall = performance_report["overall_stats"]
            print(f"  Total Executions: {overall['total_executions']}")
            print(f"  Cache Hit Rate: {overall['overall_cache_hit_rate']:.1f}%")
            print(f"  Average Execution Time: {overall['avg_execution_time']:.3f}s")
            print(f"  Total Timeouts: {overall['total_timeouts']}")
            print(f"  Total Errors: {overall['total_errors']}")
            
            print(f"\nConnection Pool:")
            pool = performance_report["connection_pool"]
            print(f"  Pool Size: {pool['pool_size']}")
            print(f"  Checked Out: {pool['checked_out']}")
            print(f"  Utilization: {pool['utilization_rate']:.1f}%")
            
            print(f"\nCache Statistics:")
            cache = performance_report["cache_stats"]
            print(f"  Total Entries: {cache['total_entries']}")
            print(f"  Total Hits: {cache['total_hits']}")
            print(f"  Cache Enabled: {'Yes' if cache['cache_enabled'] else 'No'}")
            
            if args.verbose:
                print("\nDetailed Performance Report:")
                print_json(performance_report)
    else:
        print("Optimizer is not initialized. Run 'init' command first.")

async def cmd_analyze_indexes(args) -> None:
    """Analyze database indexes and provide recommendations"""
    print("Analyzing database indexes for preference queries...")
    
    try:
        recommendations = await analyze_and_recommend_indexes()
        
        print(f"\nIndex Analysis Results:")
        print(f"Total Recommendations: {len(recommendations)}")
        
        # Group by priority
        by_priority = {"high": [], "medium": [], "low": []}
        for rec in recommendations:
            by_priority[rec.priority].append(rec)
        
        for priority in ["high", "medium", "low"]:
            recs = by_priority[priority]
            if recs:
                print(f"\n{priority.upper()} Priority ({len(recs)} recommendations):")
                for rec in recs:
                    print(f"  • {rec.index_name} on {rec.table_name}")
                    print(f"    Columns: {', '.join(rec.columns)}")
                    print(f"    Benefit: {rec.estimated_benefit}")
                    if args.verbose:
                        print(f"    SQL: {rec.create_statement}")
                    print()
        
        if args.verbose:
            analyzer = PreferenceIndexAnalyzer()
            analyzer.recommendations = recommendations
            report = analyzer.generate_index_report()
            print("\nDetailed Index Report:")
            print_json(report)
            
    except Exception as e:
        print_status(f"Failed to analyze indexes: {str(e)}", False)
        sys.exit(1)

async def cmd_create_indexes(args) -> None:
    """Create recommended database indexes"""
    if not args.confirm and not args.dry_run:
        print("This will create database indexes. Use --confirm to proceed or --dry-run to preview.")
        sys.exit(1)
    
    print("Creating recommended database indexes...")
    
    try:
        results = await create_preference_indexes(dry_run=args.dry_run)
        
        if args.dry_run:
            print("\nDRY RUN - No indexes were actually created")
        
        print(f"\nIndex Creation Results:")
        print(f"Created: {len(results['created'])}")
        print(f"Failed: {len(results['failed'])}")
        print(f"Skipped: {len(results['skipped'])}")
        
        if results["created"]:
            print("\nSuccessfully Created:")
            for idx in results["created"]:
                print(f"  ✓ {idx['index_name']} on {idx['table_name']} ({idx['priority']} priority)")
        
        if results["failed"]:
            print("\nFailed to Create:")
            for idx in results["failed"]:
                print(f"  ✗ {idx['index_name']} on {idx['table_name']}: {idx['error']}")
        
        if results["skipped"]:
            print("\nSkipped:")
            for idx in results["skipped"]:
                reason = idx.get("reason", "unknown")
                print(f"  - {idx['index_name']} on {idx['table_name']} ({reason})")
        
        if args.verbose:
            print("\nDetailed Results:")
            print_json(results)
            
    except Exception as e:
        print_status(f"Failed to create indexes: {str(e)}", False)
        sys.exit(1)

async def cmd_performance_report(args) -> None:
    """Generate comprehensive performance report"""
    optimizer = get_preference_query_optimizer()
    if not optimizer:
        print_status("Optimizer is not initialized. Run 'init' command first.", False)
        sys.exit(1)
    
    print("Generating performance report...")
    
    try:
        report = optimizer.generate_performance_report()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print_status(f"Performance report saved to {args.output}")
        else:
            print_json(report)
            
    except Exception as e:
        print_status(f"Failed to generate performance report: {str(e)}", False)
        sys.exit(1)

async def cmd_clear_cache(args) -> None:
    """Clear query cache"""
    optimizer = get_preference_query_optimizer()
    if not optimizer:
        print_status("Optimizer is not initialized. Run 'init' command first.", False)
        sys.exit(1)
    
    if not args.confirm:
        print("This will clear the query cache. Use --confirm to proceed.")
        sys.exit(1)
    
    try:
        cleared_count = optimizer.clear_cache()
        print_status(f"Cleared {cleared_count} cache entries")
        
    except Exception as e:
        print_status(f"Failed to clear cache: {str(e)}", False)
        sys.exit(1)

async def cmd_cleanup(args) -> None:
    """Cleanup optimization resources"""
    print("Cleaning up preference query optimization resources...")
    
    try:
        await cleanup_preference_optimization()
        print_status("Cleanup completed successfully")
        
    except Exception as e:
        print_status(f"Failed to cleanup: {str(e)}", False)
        sys.exit(1)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Preference Query Optimization Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize for development
  python preference_query_optimization_cli.py init --environment development
  
  # Initialize for production with index creation
  python preference_query_optimization_cli.py init --environment production
  
  # Check current status
  python preference_query_optimization_cli.py status
  
  # Analyze index recommendations
  python preference_query_optimization_cli.py analyze-indexes --verbose
  
  # Create recommended indexes (dry run first)
  python preference_query_optimization_cli.py create-indexes --dry-run
  python preference_query_optimization_cli.py create-indexes --confirm
  
  # Generate performance report
  python preference_query_optimization_cli.py performance-report --output report.json
  
  # Clear cache
  python preference_query_optimization_cli.py clear-cache --confirm
        """
    )
    
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize optimization")
    init_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    init_parser.add_argument("--environment", choices=["development", "production", "testing", "custom"], 
                           default="custom", help="Environment preset")
    init_parser.add_argument("--disable-optimizer", action="store_true", help="Disable query optimizer")
    init_parser.add_argument("--create-indexes", action="store_true", help="Create recommended indexes")
    init_parser.add_argument("--pool-size", type=int, help="Connection pool size")
    init_parser.add_argument("--query-timeout", type=int, help="Query timeout in seconds")
    init_parser.add_argument("--cache-ttl", type=int, help="Cache TTL in seconds")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show optimization status")
    status_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # Analyze indexes command
    analyze_parser = subparsers.add_parser("analyze-indexes", help="Analyze database indexes")
    analyze_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # Create indexes command
    create_parser = subparsers.add_parser("create-indexes", help="Create recommended indexes")
    create_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    create_parser.add_argument("--confirm", action="store_true", help="Confirm index creation")
    create_parser.add_argument("--dry-run", action="store_true", help="Dry run (preview only)")
    
    # Performance report command
    report_parser = subparsers.add_parser("performance-report", help="Generate performance report")
    report_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    report_parser.add_argument("--output", "-o", help="Output file path")
    
    # Clear cache command
    cache_parser = subparsers.add_parser("clear-cache", help="Clear query cache")
    cache_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    cache_parser.add_argument("--confirm", action="store_true", help="Confirm cache clearing")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup optimization resources")
    cleanup_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Map commands to functions
    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "analyze-indexes": cmd_analyze_indexes,
        "create-indexes": cmd_create_indexes,
        "performance-report": cmd_performance_report,
        "clear-cache": cmd_clear_cache,
        "cleanup": cmd_cleanup
    }
    
    # Run the command
    try:
        asyncio.run(commands[args.command](args))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_status(f"Unexpected error: {str(e)}", False)
        sys.exit(1)

if __name__ == "__main__":
    main()