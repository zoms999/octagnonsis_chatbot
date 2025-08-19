"""
Preference Monitoring System Demo

Demonstrates the preference data processing monitoring and alerting system.
Shows how to use metrics collection, alerting, and reporting features.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from monitoring.preference_metrics import (
    get_preference_metrics_collector,
    PreferenceQueryType,
    AlertSeverity
)
from monitoring.preference_alerting import get_preference_alerting_system

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_metrics_collection():
    """Demonstrate metrics collection functionality"""
    print("\n=== Preference Metrics Collection Demo ===")
    
    collector = get_preference_metrics_collector()
    
    # Simulate some query executions
    print("Recording query execution metrics...")
    
    # Successful queries
    await collector.record_query_execution(
        query_type=PreferenceQueryType.IMAGE_PREFERENCE_STATS,
        anp_seq=12345,
        execution_time_ms=150.5,
        success=True,
        row_count=1
    )
    
    await collector.record_query_execution(
        query_type=PreferenceQueryType.PREFERENCE_DATA,
        anp_seq=12345,
        execution_time_ms=200.3,
        success=True,
        row_count=3
    )
    
    # Failed query
    await collector.record_query_execution(
        query_type=PreferenceQueryType.PREFERENCE_JOBS,
        anp_seq=12345,
        execution_time_ms=5000.0,
        success=False,
        row_count=0,
        error_message="Connection timeout"
    )
    
    # Document creation metrics
    print("Recording document creation metrics...")
    
    await collector.record_document_creation(
        anp_seq=12345,
        documents_created=2,
        documents_failed=1,
        total_processing_time_ms=2500.0,
        data_completeness_score=0.67,
        success=True
    )
    
    # Get success rates
    print("\nQuery Success Rates (last 24 hours):")
    rates = await collector.get_query_success_rates(24)
    for query_type, rate in rates.items():
        print(f"  {query_type}: {rate:.1%}")
    
    # Get document creation metrics
    print("\nDocument Creation Metrics (last 24 hours):")
    doc_metrics = await collector.get_document_creation_rates(24)
    print(f"  Success Rate: {doc_metrics['success_rate']:.1%}")
    print(f"  Avg Completeness: {doc_metrics['avg_completeness_score']:.1%}")
    print(f"  Total Processed: {doc_metrics['total_processed']}")
    print(f"  Avg Processing Time: {doc_metrics['avg_processing_time_ms']:.0f}ms")

async def demo_alerting_system():
    """Demonstrate alerting system functionality"""
    print("\n=== Preference Alerting System Demo ===")
    
    alerting = get_preference_alerting_system()
    
    # Show default alert rules
    print("Default Alert Rules:")
    for rule in alerting.alert_rules[:3]:  # Show first 3 rules
        print(f"  - {rule.name}: {rule.description}")
        print(f"    Severity: {rule.severity.value}, Interval: {rule.check_interval_minutes}min")
    
    # Generate a test alert
    print("\nGenerating test alert...")
    collector = get_preference_metrics_collector()
    
    alert = await collector.generate_alert(
        severity=AlertSeverity.WARNING,
        title="Demo Alert",
        message="This is a demonstration alert for preference monitoring",
        affected_users=[12345, 67890],
        metrics={"demo_metric": 42}
    )
    
    print(f"Generated alert: {alert.title}")
    print(f"  Severity: {alert.severity.value}")
    print(f"  Affected Users: {len(alert.affected_users)}")
    
    # Check alert rules (this will likely not trigger with our demo data)
    print("\nChecking alert rules...")
    triggered_alerts = await alerting.check_alert_rules()
    print(f"Triggered alerts: {len(triggered_alerts)}")
    
    # Get recent alerts
    recent_alerts = await collector.get_recent_alerts(1)  # Last hour
    print(f"Recent alerts: {len(recent_alerts)}")
    for alert in recent_alerts:
        print(f"  - {alert.title} ({alert.severity.value})")

async def demo_user_impact_reporting():
    """Demonstrate user impact reporting"""
    print("\n=== User Impact Reporting Demo ===")
    
    alerting = get_preference_alerting_system()
    
    # Generate user impact reports for different scenarios
    print("Generating user impact reports...")
    
    # User with critical issues (all queries failed)
    critical_query_results = {
        "imagePreferenceStatsQuery": {"success": False, "error": "Database connection failed"},
        "preferenceDataQuery": {"success": False, "error": "Query timeout"},
        "preferenceJobsQuery": {"success": False, "error": "Table not found"}
    }
    
    critical_report = await alerting.generate_user_impact_report(11111, critical_query_results)
    print(f"\nCritical User (anp_seq: {critical_report.anp_seq}):")
    print(f"  Data Completeness: {critical_report.data_completeness_score:.1%}")
    print(f"  Issues: {len(critical_report.issues)}")
    print(f"  Missing Queries: {critical_report.missing_queries}")
    print(f"  Recommendations: {len(critical_report.recommended_actions)}")
    
    # User with moderate issues (partial success)
    moderate_query_results = {
        "imagePreferenceStatsQuery": {"success": True, "data": [{"total_count": 10}]},
        "preferenceDataQuery": {"success": False, "error": "Partial data missing"},
        "preferenceJobsQuery": {"success": True, "data": [{"job": "Engineer"}]}
    }
    
    moderate_report = await alerting.generate_user_impact_report(22222, moderate_query_results)
    print(f"\nModerate User (anp_seq: {moderate_report.anp_seq}):")
    print(f"  Data Completeness: {moderate_report.data_completeness_score:.1%}")
    print(f"  Issues: {len(moderate_report.issues)}")
    print(f"  Missing Queries: {moderate_report.missing_queries}")
    
    # Get affected users summary
    print("\nAffected Users Summary (last 24 hours):")
    summary = await alerting.get_affected_users_summary(24)
    print(f"  Total Affected: {summary['total_affected_users']}")
    print(f"  Critical Issues: {summary['critical_issues']}")
    print(f"  Moderate Issues: {summary['moderate_issues']}")
    print(f"  Minor Issues: {summary['minor_issues']}")
    print(f"  Avg Completeness: {summary['avg_completeness_score']:.1%}")
    
    if summary['most_common_issues']:
        print("  Most Common Issues:")
        for issue, count in summary['most_common_issues'][:3]:
            print(f"    - {issue}: {count} occurrences")

async def demo_comprehensive_monitoring():
    """Demonstrate comprehensive monitoring workflow"""
    print("\n=== Comprehensive Monitoring Demo ===")
    
    collector = get_preference_metrics_collector()
    
    # Simulate a batch of processing with mixed results
    print("Simulating batch processing with mixed results...")
    
    users_to_process = [10001, 10002, 10003, 10004, 10005]
    
    for i, anp_seq in enumerate(users_to_process):
        # Simulate different success patterns
        if i == 0:
            # Perfect success
            success_rates = [True, True, True]
            doc_completeness = 1.0
        elif i == 1:
            # Partial success
            success_rates = [True, False, True]
            doc_completeness = 0.67
        elif i == 2:
            # Major failure
            success_rates = [False, False, False]
            doc_completeness = 0.0
        else:
            # Good success
            success_rates = [True, True, True]
            doc_completeness = 1.0
        
        # Record query metrics
        query_types = [
            PreferenceQueryType.IMAGE_PREFERENCE_STATS,
            PreferenceQueryType.PREFERENCE_DATA,
            PreferenceQueryType.PREFERENCE_JOBS
        ]
        
        for j, (query_type, success) in enumerate(zip(query_types, success_rates)):
            await collector.record_query_execution(
                query_type=query_type,
                anp_seq=anp_seq,
                execution_time_ms=100 + j * 50 + (1000 if not success else 0),
                success=success,
                row_count=1 if success else 0,
                error_message="Processing error" if not success else None
            )
        
        # Record document creation
        docs_created = sum(success_rates)
        docs_failed = len(success_rates) - docs_created
        
        await collector.record_document_creation(
            anp_seq=anp_seq,
            documents_created=docs_created,
            documents_failed=docs_failed,
            total_processing_time_ms=500 + i * 100,
            data_completeness_score=doc_completeness,
            success=doc_completeness > 0.5
        )
    
    # Get comprehensive metrics summary
    print("\nComprehensive Metrics Summary:")
    summary = await collector.export_metrics_summary()
    
    print(f"Overall Query Success Rate: {summary['summary']['overall_query_success_rate']:.1%}")
    print(f"Document Success Rate: {summary['summary']['document_success_rate']:.1%}")
    print(f"Avg Data Completeness: {summary['summary']['avg_data_completeness']:.1%}")
    print(f"Total Alerts: {summary['summary']['total_alerts_count']}")
    
    # Check if any alerts were triggered
    alerting = get_preference_alerting_system()
    alerts = await alerting.check_alert_rules()
    
    if alerts:
        print(f"\nTriggered Alerts: {len(alerts)}")
        for alert in alerts:
            print(f"  - {alert.title} ({alert.severity.value})")
    else:
        print("\nNo alerts triggered - system performing within acceptable parameters")

async def main():
    """Run all monitoring demos"""
    print("Preference Data Processing Monitoring System Demo")
    print("=" * 50)
    
    try:
        await demo_metrics_collection()
        await demo_alerting_system()
        await demo_user_impact_reporting()
        await demo_comprehensive_monitoring()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ Query execution metrics collection")
        print("✓ Document creation metrics tracking")
        print("✓ Automated alerting based on configurable rules")
        print("✓ User impact analysis and reporting")
        print("✓ Comprehensive monitoring dashboard data")
        print("\nThe monitoring system is now ready for production use!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())