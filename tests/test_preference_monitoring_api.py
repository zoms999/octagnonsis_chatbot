"""
Tests for preference monitoring API endpoints
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.preference_monitoring_endpoints import router
from monitoring.preference_metrics import (
    PreferenceMetricsCollector,
    PreferenceQueryType,
    AlertSeverity
)
from monitoring.preference_alerting import PreferenceAlertingSystem

# Create test app
app = FastAPI()
app.include_router(router)

class TestPreferenceMonitoringAPI:
    """Test preference monitoring API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """Mock metrics collector"""
        collector = Mock(spec=PreferenceMetricsCollector)
        collector.get_query_success_rates = AsyncMock()
        collector.get_document_creation_rates = AsyncMock()
        collector.get_recent_alerts = AsyncMock()
        collector.export_metrics_summary = AsyncMock()
        return collector
    
    @pytest.fixture
    def mock_alerting_system(self):
        """Mock alerting system"""
        system = Mock(spec=PreferenceAlertingSystem)
        system.get_affected_users_summary = AsyncMock()
        system.check_alert_rules = AsyncMock()
        system.alert_rules = []
        system._lock = AsyncMock()
        return system
    
    def test_get_metrics_summary_success(self, client, mock_metrics_collector):
        """Test successful metrics summary retrieval"""
        # Mock return values
        mock_metrics_collector.get_query_success_rates.return_value = {
            "imagePreferenceStatsQuery": 0.95,
            "preferenceDataQuery": 0.90,
            "preferenceJobsQuery": 0.85
        }
        
        mock_metrics_collector.get_document_creation_rates.return_value = {
            "success_rate": 0.92,
            "avg_completeness_score": 0.88,
            "total_processed": 100,
            "avg_processing_time_ms": 1500.0
        }
        
        mock_metrics_collector.get_recent_alerts.return_value = []
        
        with patch('api.preference_monitoring_endpoints.get_preference_metrics_collector', return_value=mock_metrics_collector):
            response = client.get("/api/monitoring/preference/metrics/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query_success_rates" in data
        assert "document_creation_metrics" in data
        assert "recent_alerts" in data
        assert "summary" in data
        
        assert data["query_success_rates"]["imagePreferenceStatsQuery"] == 0.95
        assert data["document_creation_metrics"]["success_rate"] == 0.92
    
    def test_get_metrics_summary_with_time_window(self, client, mock_metrics_collector):
        """Test metrics summary with custom time window"""
        mock_metrics_collector.get_query_success_rates.return_value = {}
        mock_metrics_collector.get_document_creation_rates.return_value = {
            "success_rate": 0.0,
            "avg_completeness_score": 0.0,
            "total_processed": 0,
            "avg_processing_time_ms": 0.0
        }
        mock_metrics_collector.get_recent_alerts.return_value = []
        
        with patch('api.preference_monitoring_endpoints.get_preference_metrics_collector', return_value=mock_metrics_collector):
            response = client.get("/api/monitoring/preference/metrics/summary?time_window_hours=48")
        
        assert response.status_code == 200
        
        # Verify the time window was passed correctly
        mock_metrics_collector.get_query_success_rates.assert_called_with(48)
        mock_metrics_collector.get_document_creation_rates.assert_called_with(48)
        mock_metrics_collector.get_recent_alerts.assert_called_with(48)
    
    def test_get_metrics_summary_invalid_time_window(self, client):
        """Test metrics summary with invalid time window"""
        response = client.get("/api/monitoring/preference/metrics/summary?time_window_hours=200")
        assert response.status_code == 422  # Validation error
        
        response = client.get("/api/monitoring/preference/metrics/summary?time_window_hours=0")
        assert response.status_code == 422  # Validation error
    
    def test_get_query_success_rates(self, client, mock_metrics_collector):
        """Test query success rates endpoint"""
        mock_metrics_collector.get_query_success_rates.return_value = {
            "imagePreferenceStatsQuery": 0.80,
            "preferenceDataQuery": 0.75,
            "preferenceJobsQuery": 0.70
        }
        
        with patch('api.preference_monitoring_endpoints.get_preference_metrics_collector', return_value=mock_metrics_collector):
            response = client.get("/api/monitoring/preference/metrics/query-success-rates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["imagePreferenceStatsQuery"] == 0.80
        assert data["preferenceDataQuery"] == 0.75
        assert data["preferenceJobsQuery"] == 0.70
        assert data["time_window_hours"] == 24  # Default value
    
    def test_get_document_creation_metrics(self, client, mock_metrics_collector):
        """Test document creation metrics endpoint"""
        mock_metrics_collector.get_document_creation_rates.return_value = {
            "success_rate": 0.85,
            "avg_completeness_score": 0.78,
            "total_processed": 50,
            "avg_processing_time_ms": 2000.0
        }
        
        with patch('api.preference_monitoring_endpoints.get_preference_metrics_collector', return_value=mock_metrics_collector):
            response = client.get("/api/monitoring/preference/metrics/document-creation")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success_rate"] == 0.85
        assert data["avg_completeness_score"] == 0.78
        assert data["total_processed"] == 50
        assert data["avg_processing_time_ms"] == 2000.0
    
    def test_get_recent_alerts(self, client, mock_metrics_collector):
        """Test recent alerts endpoint"""
        from monitoring.preference_metrics import PreferenceAlert
        
        test_alert = PreferenceAlert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            affected_users=[1, 2, 3],
            metrics={"test": "data"},
            timestamp=datetime.utcnow()
        )
        
        mock_metrics_collector.get_recent_alerts.return_value = [test_alert]
        
        with patch('api.preference_monitoring_endpoints.get_preference_metrics_collector', return_value=mock_metrics_collector):
            response = client.get("/api/monitoring/preference/alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["severity"] == "warning"
        assert data[0]["title"] == "Test Alert"
        assert data[0]["message"] == "Test message"
        assert data[0]["affected_users_count"] == 3
    
    def test_get_recent_alerts_with_severity_filter(self, client, mock_metrics_collector):
        """Test recent alerts with severity filter"""
        mock_metrics_collector.get_recent_alerts.return_value = []
        
        with patch('api.preference_monitoring_endpoints.get_preference_metrics_collector', return_value=mock_metrics_collector):
            response = client.get("/api/monitoring/preference/alerts?severity=critical")
        
        assert response.status_code == 200
        
        # Verify severity filter was applied
        mock_metrics_collector.get_recent_alerts.assert_called_with(24, AlertSeverity.CRITICAL)
    
    def test_get_recent_alerts_invalid_severity(self, client):
        """Test recent alerts with invalid severity"""
        response = client.get("/api/monitoring/preference/alerts?severity=invalid")
        assert response.status_code == 400
    
    def test_get_user_impact_summary(self, client, mock_alerting_system):
        """Test user impact summary endpoint"""
        mock_alerting_system.get_affected_users_summary.return_value = {
            "total_affected_users": 25,
            "critical_issues": 5,
            "moderate_issues": 10,
            "minor_issues": 10,
            "avg_completeness_score": 0.65,
            "most_common_issues": [("Query failure: preferenceDataQuery", 15), ("Query failure: preferenceJobsQuery", 8)]
        }
        
        with patch('api.preference_monitoring_endpoints.get_preference_alerting_system', return_value=mock_alerting_system):
            response = client.get("/api/monitoring/preference/user-impact")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_affected_users"] == 25
        assert data["critical_issues"] == 5
        assert data["moderate_issues"] == 10
        assert data["minor_issues"] == 10
        assert data["avg_completeness_score"] == 0.65
        assert len(data["most_common_issues"]) == 2
    
    def test_get_alert_rules(self, client, mock_alerting_system):
        """Test get alert rules endpoint"""
        from monitoring.preference_alerting import AlertRule
        
        test_rule = AlertRule(
            name="test_rule",
            description="Test rule description",
            severity=AlertSeverity.WARNING,
            condition_func=lambda x: True,
            message_template="Test message",
            check_interval_minutes=5,
            enabled=True
        )
        
        mock_alerting_system.alert_rules = [test_rule]
        
        with patch('api.preference_monitoring_endpoints.get_preference_alerting_system', return_value=mock_alerting_system):
            response = client.get("/api/monitoring/preference/alert-rules")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["name"] == "test_rule"
        assert data[0]["description"] == "Test rule description"
        assert data[0]["severity"] == "warning"
        assert data[0]["check_interval_minutes"] == 5
        assert data[0]["enabled"] is True
    
    def test_toggle_alert_rule_enable(self, client, mock_alerting_system):
        """Test enabling an alert rule"""
        from monitoring.preference_alerting import AlertRule
        
        test_rule = AlertRule(
            name="test_rule",
            description="Test rule",
            severity=AlertSeverity.INFO,
            condition_func=lambda x: False,
            message_template="Test",
            enabled=False
        )
        
        mock_alerting_system.alert_rules = [test_rule]
        mock_alerting_system._lock = AsyncMock()
        
        with patch('api.preference_monitoring_endpoints.get_preference_alerting_system', return_value=mock_alerting_system):
            response = client.post("/api/monitoring/preference/alert-rules/test_rule/toggle?enabled=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["rule_name"] == "test_rule"
        assert data["enabled"] is True
        assert test_rule.enabled is True
    
    def test_toggle_alert_rule_not_found(self, client, mock_alerting_system):
        """Test toggling non-existent alert rule"""
        mock_alerting_system.alert_rules = []
        mock_alerting_system._lock = AsyncMock()
        
        with patch('api.preference_monitoring_endpoints.get_preference_alerting_system', return_value=mock_alerting_system):
            response = client.post("/api/monitoring/preference/alert-rules/nonexistent/toggle?enabled=true")
        
        assert response.status_code == 404
    
    def test_trigger_alert_check(self, client, mock_alerting_system):
        """Test manual alert check trigger"""
        from monitoring.preference_metrics import PreferenceAlert
        
        test_alert = PreferenceAlert(
            severity=AlertSeverity.CRITICAL,
            title="Manual Check Alert",
            message="Alert from manual check",
            affected_users=[],
            metrics={}
        )
        
        mock_alerting_system.check_alert_rules.return_value = [test_alert]
        
        with patch('api.preference_monitoring_endpoints.get_preference_alerting_system', return_value=mock_alerting_system):
            response = client.post("/api/monitoring/preference/check-alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["alerts_triggered"] == 1
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["severity"] == "critical"
        assert data["alerts"][0]["title"] == "Manual Check Alert"
    
    def test_api_error_handling(self, client):
        """Test API error handling when services fail"""
        with patch('api.preference_monitoring_endpoints.get_preference_metrics_collector') as mock_get_collector:
            mock_collector = Mock()
            mock_collector.get_query_success_rates.side_effect = Exception("Database error")
            mock_get_collector.return_value = mock_collector
            
            response = client.get("/api/monitoring/preference/metrics/query-success-rates")
            assert response.status_code == 500
    
    def test_api_validation_errors(self, client):
        """Test API validation for invalid parameters"""
        # Invalid time window (too large)
        response = client.get("/api/monitoring/preference/metrics/summary?time_window_hours=200")
        assert response.status_code == 422
        
        # Invalid time window (negative)
        response = client.get("/api/monitoring/preference/metrics/summary?time_window_hours=-1")
        assert response.status_code == 422
        
        # Invalid severity filter
        response = client.get("/api/monitoring/preference/alerts?severity=invalid_severity")
        assert response.status_code == 400

class TestPreferenceMonitoringAPIIntegration:
    """Integration tests for preference monitoring API"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_full_monitoring_api_flow(self, client):
        """Test complete monitoring API workflow"""
        # This would be an integration test that uses real instances
        # For now, we'll test with mocked dependencies
        
        with patch('api.preference_monitoring_endpoints.get_preference_metrics_collector') as mock_get_collector, \
             patch('api.preference_monitoring_endpoints.get_preference_alerting_system') as mock_get_alerting:
            
            # Setup mocks
            mock_collector = Mock()
            mock_collector.get_query_success_rates = AsyncMock(return_value={"imagePreferenceStatsQuery": 0.5})
            mock_collector.get_document_creation_rates = AsyncMock(return_value={
                "success_rate": 0.7,
                "avg_completeness_score": 0.8,
                "total_processed": 10,
                "avg_processing_time_ms": 1500.0
            })
            mock_collector.get_recent_alerts = AsyncMock(return_value=[])
            mock_get_collector.return_value = mock_collector
            
            mock_alerting = Mock()
            mock_alerting.get_affected_users_summary = AsyncMock(return_value={
                "total_affected_users": 0,
                "critical_issues": 0,
                "moderate_issues": 0,
                "minor_issues": 0,
                "avg_completeness_score": 0.0,
                "most_common_issues": []
            })
            mock_alerting.check_alert_rules = AsyncMock(return_value=[])
            mock_alerting.alert_rules = []
            mock_alerting._lock = AsyncMock()
            mock_get_alerting.return_value = mock_alerting
            
            # Test metrics summary
            response = client.get("/api/monitoring/preference/metrics/summary")
            assert response.status_code == 200
            
            # Test user impact
            response = client.get("/api/monitoring/preference/user-impact")
            assert response.status_code == 200
            
            # Test alert check
            response = client.post("/api/monitoring/preference/check-alerts")
            assert response.status_code == 200
            
            # Test alert rules
            response = client.get("/api/monitoring/preference/alert-rules")
            assert response.status_code == 200