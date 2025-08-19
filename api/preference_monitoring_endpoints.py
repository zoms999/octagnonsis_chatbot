"""
Preference Data Monitoring API Endpoints

Provides REST API endpoints for monitoring preference data processing,
viewing metrics, alerts, and user impact reports.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from monitoring.preference_metrics import (
    get_preference_metrics_collector,
    PreferenceMetricsCollector,
    AlertSeverity
)
from monitoring.preference_alerting import (
    get_preference_alerting_system,
    PreferenceAlertingSystem,
    AlertRule
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitoring/preference", tags=["preference-monitoring"])

# Response models
class QuerySuccessRatesResponse(BaseModel):
    """Response model for query success rates"""
    imagePreferenceStatsQuery: float = Field(description="Success rate for image preference stats query")
    preferenceDataQuery: float = Field(description="Success rate for preference data query")
    preferenceJobsQuery: float = Field(description="Success rate for preference jobs query")
    time_window_hours: int = Field(description="Time window for calculation")

class DocumentCreationMetricsResponse(BaseModel):
    """Response model for document creation metrics"""
    success_rate: float = Field(description="Document creation success rate")
    avg_completeness_score: float = Field(description="Average data completeness score")
    total_processed: int = Field(description="Total documents processed")
    avg_processing_time_ms: float = Field(description="Average processing time in milliseconds")
    time_window_hours: int = Field(description="Time window for calculation")

class AlertResponse(BaseModel):
    """Response model for alerts"""
    severity: str = Field(description="Alert severity level")
    title: str = Field(description="Alert title")
    message: str = Field(description="Alert message")
    affected_users_count: int = Field(description="Number of affected users")
    timestamp: datetime = Field(description="Alert timestamp")

class MetricsSummaryResponse(BaseModel):
    """Response model for metrics summary"""
    query_success_rates: QuerySuccessRatesResponse
    document_creation_metrics: DocumentCreationMetricsResponse
    recent_alerts: List[AlertResponse]
    summary: Dict[str, Any] = Field(description="Overall summary statistics")

class UserImpactSummaryResponse(BaseModel):
    """Response model for user impact summary"""
    total_affected_users: int = Field(description="Total number of affected users")
    critical_issues: int = Field(description="Users with critical issues (< 30% completeness)")
    moderate_issues: int = Field(description="Users with moderate issues (30-70% completeness)")
    minor_issues: int = Field(description="Users with minor issues (> 70% completeness)")
    avg_completeness_score: float = Field(description="Average data completeness score")
    most_common_issues: List[tuple] = Field(description="Most common issues and their counts")

class AlertRuleResponse(BaseModel):
    """Response model for alert rules"""
    name: str = Field(description="Rule name")
    description: str = Field(description="Rule description")
    severity: str = Field(description="Alert severity")
    check_interval_minutes: int = Field(description="Check interval in minutes")
    enabled: bool = Field(description="Whether rule is enabled")

# Dependency injection
async def get_metrics_collector() -> PreferenceMetricsCollector:
    """Get preference metrics collector instance"""
    return get_preference_metrics_collector()

async def get_alerting_system() -> PreferenceAlertingSystem:
    """Get preference alerting system instance"""
    return get_preference_alerting_system()

@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours (1-168)"),
    metrics_collector: PreferenceMetricsCollector = Depends(get_metrics_collector)
) -> MetricsSummaryResponse:
    """
    Get comprehensive preference processing metrics summary
    
    Returns query success rates, document creation metrics, recent alerts,
    and overall summary statistics for the specified time window.
    """
    try:
        # Get metrics from collector
        query_rates = await metrics_collector.get_query_success_rates(time_window_hours)
        document_metrics = await metrics_collector.get_document_creation_rates(time_window_hours)
        recent_alerts = await metrics_collector.get_recent_alerts(time_window_hours)
        
        # Build response
        query_success_rates = QuerySuccessRatesResponse(
            imagePreferenceStatsQuery=query_rates.get("imagePreferenceStatsQuery", 0.0),
            preferenceDataQuery=query_rates.get("preferenceDataQuery", 0.0),
            preferenceJobsQuery=query_rates.get("preferenceJobsQuery", 0.0),
            time_window_hours=time_window_hours
        )
        
        document_creation_metrics = DocumentCreationMetricsResponse(
            **document_metrics,
            time_window_hours=time_window_hours
        )
        
        alerts_response = [
            AlertResponse(
                severity=alert.severity.value,
                title=alert.title,
                message=alert.message,
                affected_users_count=len(alert.affected_users),
                timestamp=alert.timestamp
            )
            for alert in recent_alerts
        ]
        
        # Calculate summary
        overall_query_success_rate = sum(query_rates.values()) / len(query_rates) if query_rates else 0.0
        critical_alerts_count = len([a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL])
        
        summary = {
            "overall_query_success_rate": overall_query_success_rate,
            "document_success_rate": document_metrics.get("success_rate", 0.0),
            "avg_data_completeness": document_metrics.get("avg_completeness_score", 0.0),
            "critical_alerts_count": critical_alerts_count,
            "total_alerts_count": len(recent_alerts)
        }
        
        return MetricsSummaryResponse(
            query_success_rates=query_success_rates,
            document_creation_metrics=document_creation_metrics,
            recent_alerts=alerts_response,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics summary")

@router.get("/metrics/query-success-rates", response_model=QuerySuccessRatesResponse)
async def get_query_success_rates(
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours (1-168)"),
    metrics_collector: PreferenceMetricsCollector = Depends(get_metrics_collector)
) -> QuerySuccessRatesResponse:
    """
    Get preference query success rates by query type
    
    Returns success rates for each type of preference query within the specified time window.
    """
    try:
        rates = await metrics_collector.get_query_success_rates(time_window_hours)
        
        return QuerySuccessRatesResponse(
            imagePreferenceStatsQuery=rates.get("imagePreferenceStatsQuery", 0.0),
            preferenceDataQuery=rates.get("preferenceDataQuery", 0.0),
            preferenceJobsQuery=rates.get("preferenceJobsQuery", 0.0),
            time_window_hours=time_window_hours
        )
        
    except Exception as e:
        logger.error(f"Error getting query success rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve query success rates")

@router.get("/metrics/document-creation", response_model=DocumentCreationMetricsResponse)
async def get_document_creation_metrics(
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours (1-168)"),
    metrics_collector: PreferenceMetricsCollector = Depends(get_metrics_collector)
) -> DocumentCreationMetricsResponse:
    """
    Get preference document creation metrics
    
    Returns success rates, completeness scores, and processing times for preference document creation.
    """
    try:
        metrics = await metrics_collector.get_document_creation_rates(time_window_hours)
        
        return DocumentCreationMetricsResponse(
            **metrics,
            time_window_hours=time_window_hours
        )
        
    except Exception as e:
        logger.error(f"Error getting document creation metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document creation metrics")

@router.get("/alerts", response_model=List[AlertResponse])
async def get_recent_alerts(
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours (1-168)"),
    severity: Optional[str] = Query(None, description="Filter by severity (info, warning, critical)"),
    metrics_collector: PreferenceMetricsCollector = Depends(get_metrics_collector)
) -> List[AlertResponse]:
    """
    Get recent preference processing alerts
    
    Returns alerts generated within the specified time window, optionally filtered by severity.
    """
    try:
        severity_filter = None
        if severity:
            try:
                severity_filter = AlertSeverity(severity.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        alerts = await metrics_collector.get_recent_alerts(time_window_hours, severity_filter)
        
        return [
            AlertResponse(
                severity=alert.severity.value,
                title=alert.title,
                message=alert.message,
                affected_users_count=len(alert.affected_users),
                timestamp=alert.timestamp
            )
            for alert in alerts
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recent alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")

@router.get("/user-impact", response_model=UserImpactSummaryResponse)
async def get_user_impact_summary(
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours (1-168)"),
    alerting_system: PreferenceAlertingSystem = Depends(get_alerting_system)
) -> UserImpactSummaryResponse:
    """
    Get summary of users affected by preference data issues
    
    Returns counts of users by issue severity and most common problems.
    """
    try:
        summary = await alerting_system.get_affected_users_summary(time_window_hours)
        
        return UserImpactSummaryResponse(**summary)
        
    except Exception as e:
        logger.error(f"Error getting user impact summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user impact summary")

@router.get("/alert-rules", response_model=List[AlertRuleResponse])
async def get_alert_rules(
    alerting_system: PreferenceAlertingSystem = Depends(get_alerting_system)
) -> List[AlertRuleResponse]:
    """
    Get configured alert rules
    
    Returns all configured alerting rules with their settings.
    """
    try:
        rules = alerting_system.alert_rules
        
        return [
            AlertRuleResponse(
                name=rule.name,
                description=rule.description,
                severity=rule.severity.value,
                check_interval_minutes=rule.check_interval_minutes,
                enabled=rule.enabled
            )
            for rule in rules
        ]
        
    except Exception as e:
        logger.error(f"Error getting alert rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert rules")

@router.post("/alert-rules/{rule_name}/toggle")
async def toggle_alert_rule(
    rule_name: str,
    enabled: bool = Query(description="Whether to enable or disable the rule"),
    alerting_system: PreferenceAlertingSystem = Depends(get_alerting_system)
) -> Dict[str, Any]:
    """
    Enable or disable an alert rule
    
    Toggles the enabled state of the specified alert rule.
    """
    try:
        # Find and update the rule
        rule_found = False
        async with alerting_system._lock:
            for rule in alerting_system.alert_rules:
                if rule.name == rule_name:
                    rule.enabled = enabled
                    rule_found = True
                    break
        
        if not rule_found:
            raise HTTPException(status_code=404, detail=f"Alert rule not found: {rule_name}")
        
        logger.info(f"Alert rule {rule_name} {'enabled' if enabled else 'disabled'}")
        
        return {
            "rule_name": rule_name,
            "enabled": enabled,
            "message": f"Alert rule {rule_name} {'enabled' if enabled else 'disabled'}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling alert rule {rule_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle alert rule")

@router.post("/check-alerts")
async def trigger_alert_check(
    alerting_system: PreferenceAlertingSystem = Depends(get_alerting_system)
) -> Dict[str, Any]:
    """
    Manually trigger alert rule checking
    
    Forces an immediate check of all alert rules and returns any triggered alerts.
    """
    try:
        alerts = await alerting_system.check_alert_rules()
        
        return {
            "alerts_triggered": len(alerts),
            "alerts": [
                {
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in alerts
            ]
        }
        
    except Exception as e:
        logger.error(f"Error triggering alert check: {e}")
        raise HTTPException(status_code=500, detail="Failed to check alerts")