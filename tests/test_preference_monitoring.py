"""
Tests for preference data processing monitoring and alerting system
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from monitoring.preference_metrics import (
    PreferenceMetricsCollector,
    PreferenceQueryMetrics,
    PreferenceDocumentMetrics,
    PreferenceAlert,
    PreferenceQueryType,
    AlertSeverity,
    get_preference_metrics_collector
)
from monitoring.preference_alerting import (
    PreferenceAlertingSystem,
    AlertRule,
    UserImpactReport,
    get_preference_alerting_system
)

class TestPreferenceMetricsCollector:
    """Test preference metrics collection functionality"""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create a fresh metrics collector for each test"""
        return PreferenceMetricsCollector()
    
    @pytest.mark.asyncio
    async def test_record_query_execution_success(self, metrics_collector):
        """Test recording successful query execution"""
        await metrics_collector.record_query_execution(
            query_type=PreferenceQueryType.IMAGE_PREFERENCE_STATS,
            anp_seq=12345,
            execution_time_ms=150.5,
            success=True,
            row_count=1
        )
        
        # Check that metrics were recorded
        assert len(metrics_collector._query_metrics) == 1
        metric = metrics_collector._query_metrics[0]
        
        assert metric.query_type == PreferenceQueryType.IMAGE_PREFERENCE_STATS
        assert metric.anp_seq == 12345
        assert metric.execution_time_ms == 150.5
        assert metric.success is True
        assert metric.row_count == 1
        assert metric.error_message is None
    
    @pytest.mark.asyncio
    async def test_record_query_execution_failure(self, metrics_collector):
        """Test recording failed query execution"""
        await metrics_collector.record_query_execution(
            query_type=PreferenceQueryType.PREFERENCE_DATA,
            anp_seq=12345,
            execution_time_ms=5000.0,
            success=False,
            row_count=0,
            error_message="Connection timeout"
        )
        
        # Check that metrics were recorded
        assert len(metrics_collector._query_metrics) == 1
        metric = metrics_collector._query_metrics[0]
        
        assert metric.query_type == PreferenceQueryType.PREFERENCE_DATA
        assert metric.success is False
        assert metric.error_message == "Connection timeout"
    
    @pytest.mark.asyncio
    async def test_record_document_creation(self, metrics_collector):
        """Test recording document creation metrics"""
        await metrics_collector.record_document_creation(
            anp_seq=12345,
            documents_created=3,
            documents_failed=0,
            total_processing_time_ms=2500.0,
            data_completeness_score=1.0,
            success=True
        )
        
        # Check that metrics were recorded
        assert len(metrics_collector._document_metrics) == 1
        metric = metrics_collector._document_metrics[0]
        
        assert metric.anp_seq == 12345
        assert metric.documents_created == 3
        assert metric.documents_failed == 0
        assert metric.data_completeness_score == 1.0
        assert metric.success is True
    
    @pytest.mark.asyncio
    async def test_get_query_success_rates(self, metrics_collector):
        """Test calculating query success rates"""
        # Record some successful and failed queries
        await metrics_collector.record_query_execution(
            PreferenceQueryType.IMAGE_PREFERENCE_STATS, 1, 100, True, 1
        )
        await metrics_collector.record_query_execution(
            PreferenceQueryType.IMAGE_PREFERENCE_STATS, 2, 200, False, 0, "Error"
        )
        await metrics_collector.record_query_execution(
            PreferenceQueryType.PREFERENCE_DATA, 1, 150, True, 3
        )
        
        rates = await metrics_collector.get_query_success_rates(24)
        
        assert rates["imagePreferenceStatsQuery"] == 0.5  # 1 success out of 2
        assert rates["preferenceDataQuery"] == 1.0  # 1 success out of 1
        assert rates["preferenceJobsQuery"] == 0.0  # No queries recorded
    
    @pytest.mark.asyncio
    async def test_get_document_creation_rates(self, metrics_collector):
        """Test calculating document creation rates"""
        # Record some document creation metrics
        await metrics_collector.record_document_creation(1, 3, 0, 1000, 1.0, True)
        await metrics_collector.record_document_creation(2, 0, 1, 2000, 0.0, False)
        await metrics_collector.record_document_creation(3, 2, 0, 1500, 0.67, True)
        
        rates = await metrics_collector.get_document_creation_rates(24)
        
        assert rates["success_rate"] == 2/3  # 2 successes out of 3
        assert rates["avg_completeness_score"] == (1.0 + 0.0 + 0.67) / 3
        assert rates["total_processed"] == 3
        assert rates["avg_processing_time_ms"] == (1000 + 2000 + 1500) / 3
    
    @pytest.mark.asyncio
    async def test_generate_alert(self, metrics_collector):
        """Test generating alerts"""
        alert = await metrics_collector.generate_alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="This is a test alert",
            affected_users=[1, 2, 3],
            metrics={"test_metric": 42}
        )
        
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test alert"
        assert alert.affected_users == [1, 2, 3]
        assert alert.metrics["test_metric"] == 42
        
        # Check that alert was stored
        assert len(metrics_collector._alerts) == 1
    
    @pytest.mark.asyncio
    async def test_export_metrics_summary(self, metrics_collector):
        """Test exporting comprehensive metrics summary"""
        # Add some test data
        await metrics_collector.record_query_execution(
            PreferenceQueryType.IMAGE_PREFERENCE_STATS, 1, 100, True, 1
        )
        await metrics_collector.record_document_creation(1, 3, 0, 1000, 1.0, True)
        await metrics_collector.generate_alert(
            AlertSeverity.INFO, "Test", "Test message"
        )
        
        summary = await metrics_collector.export_metrics_summary()
        
        assert "query_success_rates" in summary
        assert "document_creation_metrics" in summary
        assert "recent_alerts" in summary
        assert "summary" in summary
        
        assert summary["summary"]["overall_query_success_rate"] > 0
        assert summary["summary"]["document_success_rate"] == 1.0

class TestPreferenceAlertingSystem:
    """Test preference alerting system functionality"""
    
    @pytest.fixture
    def alerting_system(self):
        """Create a fresh alerting system for each test"""
        metrics_collector = PreferenceMetricsCollector()
        return PreferenceAlertingSystem(metrics_collector)
    
    @pytest.mark.asyncio
    async def test_default_alert_rules_loaded(self, alerting_system):
        """Test that default alert rules are loaded"""
        assert len(alerting_system.alert_rules) > 0
        
        rule_names = [rule.name for rule in alerting_system.alert_rules]
        assert "preference_query_critical_failure" in rule_names
        assert "preference_document_critical_failure" in rule_names
        assert "preference_data_completeness_low" in rule_names
    
    @pytest.mark.asyncio
    async def test_add_custom_alert_rule(self, alerting_system):
        """Test adding custom alert rules"""
        custom_rule = AlertRule(
            name="custom_test_rule",
            description="Custom test rule",
            severity=AlertSeverity.WARNING,
            condition_func=lambda metrics: True,  # Always trigger
            message_template="Custom alert message"
        )
        
        initial_count = len(alerting_system.alert_rules)
        await alerting_system.add_alert_rule(custom_rule)
        
        assert len(alerting_system.alert_rules) == initial_count + 1
        assert any(rule.name == "custom_test_rule" for rule in alerting_system.alert_rules)
    
    @pytest.mark.asyncio
    async def test_remove_alert_rule(self, alerting_system):
        """Test removing alert rules"""
        # Add a test rule first
        test_rule = AlertRule(
            name="test_rule_to_remove",
            description="Test rule",
            severity=AlertSeverity.INFO,
            condition_func=lambda metrics: False,
            message_template="Test message"
        )
        await alerting_system.add_alert_rule(test_rule)
        
        # Remove the rule
        removed = await alerting_system.remove_alert_rule("test_rule_to_remove")
        assert removed is True
        
        # Verify it's gone
        assert not any(rule.name == "test_rule_to_remove" for rule in alerting_system.alert_rules)
        
        # Try to remove non-existent rule
        removed = await alerting_system.remove_alert_rule("non_existent_rule")
        assert removed is False
    
    @pytest.mark.asyncio
    async def test_check_alert_rules_no_triggers(self, alerting_system):
        """Test checking alert rules when no conditions are met"""
        # Mock metrics that don't trigger any alerts
        with patch.object(alerting_system.metrics_collector, 'export_metrics_summary') as mock_export:
            mock_export.return_value = {
                "summary": {
                    "overall_query_success_rate": 0.95,
                    "avg_data_completeness": 0.8
                },
                "document_creation_metrics": {
                    "success_rate": 0.9,
                    "total_processed": 10,
                    "avg_processing_time_ms": 1000
                },
                "query_success_rates": {}
            }
            
            alerts = await alerting_system.check_alert_rules()
            assert len(alerts) == 0
    
    @pytest.mark.asyncio
    async def test_check_alert_rules_with_triggers(self, alerting_system):
        """Test checking alert rules when conditions are met"""
        # Mock metrics that trigger critical failure alert
        with patch.object(alerting_system.metrics_collector, 'export_metrics_summary') as mock_export:
            mock_export.return_value = {
                "summary": {
                    "overall_query_success_rate": 0.3,  # Below 50% threshold
                    "avg_data_completeness": 0.2
                },
                "document_creation_metrics": {
                    "success_rate": 0.5,
                    "total_processed": 5,
                    "avg_processing_time_ms": 2000
                },
                "query_success_rates": {}
            }
            
            alerts = await alerting_system.check_alert_rules()
            assert len(alerts) > 0
            
            # Check that critical alert was generated
            critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
            assert len(critical_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_generate_user_impact_report(self, alerting_system):
        """Test generating user impact reports"""
        query_results = {
            "imagePreferenceStatsQuery": {"success": True, "data": [{"total_count": 10}]},
            "preferenceDataQuery": {"success": False, "error": "Connection timeout"},
            "preferenceJobsQuery": {"success": True, "data": [{"job": "Engineer"}]}
        }
        
        report = await alerting_system.generate_user_impact_report(12345, query_results)
        
        assert report.anp_seq == 12345
        assert report.data_completeness_score == 2/3  # 2 out of 3 queries successful
        assert len(report.missing_queries) == 1
        assert "preferenceDataQuery" in report.missing_queries
        assert len(report.issues) == 1
        assert "Connection timeout" in report.issues[0]
        assert len(report.recommended_actions) > 0
    
    @pytest.mark.asyncio
    async def test_get_affected_users_summary_empty(self, alerting_system):
        """Test getting affected users summary when no reports exist"""
        summary = await alerting_system.get_affected_users_summary(24)
        
        assert summary["total_affected_users"] == 0
        assert summary["critical_issues"] == 0
        assert summary["moderate_issues"] == 0
        assert summary["minor_issues"] == 0
        assert summary["avg_completeness_score"] == 0.0
        assert summary["most_common_issues"] == []
    
    @pytest.mark.asyncio
    async def test_get_affected_users_summary_with_data(self, alerting_system):
        """Test getting affected users summary with report data"""
        # Generate some test reports
        query_results_critical = {
            "imagePreferenceStatsQuery": {"success": False, "error": "DB Error"},
            "preferenceDataQuery": {"success": False, "error": "Timeout"},
            "preferenceJobsQuery": {"success": False, "error": "Not found"}
        }
        
        query_results_moderate = {
            "imagePreferenceStatsQuery": {"success": True, "data": []},
            "preferenceDataQuery": {"success": False, "error": "Timeout"},
            "preferenceJobsQuery": {"success": True, "data": []}
        }
        
        await alerting_system.generate_user_impact_report(1, query_results_critical)
        await alerting_system.generate_user_impact_report(2, query_results_moderate)
        
        summary = await alerting_system.get_affected_users_summary(24)
        
        assert summary["total_affected_users"] == 2
        assert summary["critical_issues"] == 1  # User 1 with 0% completeness
        assert summary["moderate_issues"] == 1  # User 2 with 33% completeness
        assert summary["minor_issues"] == 0
        assert len(summary["most_common_issues"]) > 0

class TestPreferenceMonitoringIntegration:
    """Test integration between monitoring components"""
    
    @pytest.mark.asyncio
    async def test_global_instances(self):
        """Test that global instances work correctly"""
        collector1 = get_preference_metrics_collector()
        collector2 = get_preference_metrics_collector()
        assert collector1 is collector2  # Should be same instance
        
        alerting1 = get_preference_alerting_system()
        alerting2 = get_preference_alerting_system()
        assert alerting1 is alerting2  # Should be same instance
    
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_flow(self):
        """Test complete monitoring flow from metrics to alerts"""
        collector = get_preference_metrics_collector()
        alerting = get_preference_alerting_system()
        
        # Clear any existing data
        collector._query_metrics.clear()
        collector._document_metrics.clear()
        collector._alerts.clear()
        
        # Record some failing metrics
        await collector.record_query_execution(
            PreferenceQueryType.IMAGE_PREFERENCE_STATS, 1, 1000, False, 0, "Error"
        )
        await collector.record_query_execution(
            PreferenceQueryType.PREFERENCE_DATA, 1, 2000, False, 0, "Error"
        )
        await collector.record_document_creation(
            1, 0, 1, 3000, 0.0, False, "Processing failed"
        )
        
        # Check that alerts are triggered
        alerts = await alerting.check_alert_rules()
        
        # Should have critical alerts due to 0% success rates
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        assert len(critical_alerts) > 0
        
        # Verify metrics summary reflects the failures
        summary = await collector.export_metrics_summary()
        assert summary["summary"]["overall_query_success_rate"] == 0.0
        assert summary["summary"]["document_success_rate"] == 0.0

@pytest.mark.asyncio
async def test_monitoring_performance():
    """Test that monitoring doesn't significantly impact performance"""
    import time
    
    collector = PreferenceMetricsCollector()
    
    # Time recording many metrics
    start_time = time.time()
    
    for i in range(1000):
        await collector.record_query_execution(
            PreferenceQueryType.IMAGE_PREFERENCE_STATS, i, 100, True, 1
        )
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Should complete 1000 recordings in reasonable time (< 1 second)
    assert duration < 1.0
    
    # Verify all metrics were recorded
    assert len(collector._query_metrics) == 1000

@pytest.mark.asyncio
async def test_monitoring_memory_usage():
    """Test that monitoring doesn't consume excessive memory"""
    collector = PreferenceMetricsCollector()
    
    # Record many metrics
    for i in range(10000):
        await collector.record_query_execution(
            PreferenceQueryType.PREFERENCE_DATA, i, 100, True, 1
        )
    
    # Memory usage should be reasonable
    # This is a basic check - in production you might want more sophisticated memory monitoring
    assert len(collector._query_metrics) == 10000
    
    # Test that old metrics can be cleaned up (this would be implemented in production)
    # For now, just verify the data structure is working correctly
    recent_metrics = [m for m in collector._query_metrics if m.timestamp > datetime.utcnow() - timedelta(hours=1)]
    assert len(recent_metrics) == 10000  # All should be recent in this test