"""
Preference Data Processing Metrics and Monitoring

Provides specialized metrics collection, alerting, and reporting for preference data processing.
Tracks query success rates, document creation rates, and data quality issues.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

from monitoring.metrics import MetricsRegistry, inc, observe

logger = logging.getLogger(__name__)

class PreferenceQueryType(Enum):
    """Types of preference queries"""
    IMAGE_PREFERENCE_STATS = "imagePreferenceStatsQuery"
    PREFERENCE_DATA = "preferenceDataQuery"
    PREFERENCE_JOBS = "preferenceJobsQuery"

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class PreferenceQueryMetrics:
    """Metrics for a single preference query execution"""
    query_type: PreferenceQueryType
    anp_seq: int
    execution_time_ms: float
    success: bool
    row_count: int
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class PreferenceDocumentMetrics:
    """Metrics for preference document creation"""
    anp_seq: int
    documents_created: int
    documents_failed: int
    total_processing_time_ms: float
    data_completeness_score: float  # 0.0 to 1.0
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class PreferenceAlert:
    """Preference processing alert"""
    severity: AlertSeverity
    title: str
    message: str
    affected_users: List[int]
    metrics: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class PreferenceMetricsCollector:
    """Collects and aggregates preference processing metrics"""
    
    def __init__(self):
        self._query_metrics: List[PreferenceQueryMetrics] = []
        self._document_metrics: List[PreferenceDocumentMetrics] = []
        self._alerts: List[PreferenceAlert] = []
        self._lock = asyncio.Lock()
        
    async def record_query_execution(
        self,
        query_type: PreferenceQueryType,
        anp_seq: int,
        execution_time_ms: float,
        success: bool,
        row_count: int = 0,
        error_message: Optional[str] = None
    ) -> None:
        """Record preference query execution metrics"""
        
        metrics = PreferenceQueryMetrics(
            query_type=query_type,
            anp_seq=anp_seq,
            execution_time_ms=execution_time_ms,
            success=success,
            row_count=row_count,
            error_message=error_message
        )
        
        async with self._lock:
            self._query_metrics.append(metrics)
            
        # Update global metrics registry
        await inc(
            "preference_query_total",
            labels={
                "query_type": query_type.value,
                "success": str(success)
            }
        )
        
        await observe(
            "preference_query_duration_ms",
            execution_time_ms,
            labels={"query_type": query_type.value}
        )
        
        if success:
            await observe(
                "preference_query_row_count",
                row_count,
                labels={"query_type": query_type.value}
            )
        
        logger.info(
            f"Preference query metrics recorded",
            extra={
                "query_type": query_type.value,
                "anp_seq": anp_seq,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "row_count": row_count
            }
        )
    
    async def record_document_creation(
        self,
        anp_seq: int,
        documents_created: int,
        documents_failed: int,
        total_processing_time_ms: float,
        data_completeness_score: float,
        success: bool,
        error_message: Optional[str] = None
    ) -> None:
        """Record preference document creation metrics"""
        
        metrics = PreferenceDocumentMetrics(
            anp_seq=anp_seq,
            documents_created=documents_created,
            documents_failed=documents_failed,
            total_processing_time_ms=total_processing_time_ms,
            data_completeness_score=data_completeness_score,
            success=success,
            error_message=error_message
        )
        
        async with self._lock:
            self._document_metrics.append(metrics)
            
        # Update global metrics registry
        await inc(
            "preference_document_creation_total",
            labels={"success": str(success)}
        )
        
        await observe(
            "preference_document_processing_time_ms",
            total_processing_time_ms
        )
        
        await observe(
            "preference_data_completeness_score",
            data_completeness_score
        )
        
        if success:
            await observe(
                "preference_documents_created",
                documents_created
            )
        
        logger.info(
            f"Preference document metrics recorded",
            extra={
                "anp_seq": anp_seq,
                "documents_created": documents_created,
                "documents_failed": documents_failed,
                "success": success,
                "data_completeness_score": data_completeness_score
            }
        )
    
    async def generate_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        affected_users: List[int] = None,
        metrics: Dict[str, Any] = None
    ) -> PreferenceAlert:
        """Generate and record a preference processing alert"""
        
        alert = PreferenceAlert(
            severity=severity,
            title=title,
            message=message,
            affected_users=affected_users or [],
            metrics=metrics or {}
        )
        
        async with self._lock:
            self._alerts.append(alert)
            
        # Update global metrics registry
        await inc(
            "preference_alerts_total",
            labels={"severity": severity.value}
        )
        
        logger.warning(
            f"Preference alert generated: {title}",
            extra={
                "severity": severity.value,
                "alert_message": message,
                "affected_users_count": len(alert.affected_users),
                "alert_metrics": metrics
            }
        )
        
        return alert
    
    async def get_query_success_rates(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, float]:
        """Calculate query success rates by type within time window"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        async with self._lock:
            recent_metrics = [
                m for m in self._query_metrics 
                if m.timestamp >= cutoff_time
            ]
        
        success_rates = {}
        
        for query_type in PreferenceQueryType:
            type_metrics = [
                m for m in recent_metrics 
                if m.query_type == query_type
            ]
            
            if type_metrics:
                successful = sum(1 for m in type_metrics if m.success)
                success_rates[query_type.value] = successful / len(type_metrics)
            else:
                success_rates[query_type.value] = 0.0
                
        return success_rates
    
    async def get_document_creation_rates(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Calculate document creation success rates within time window"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        async with self._lock:
            recent_metrics = [
                m for m in self._document_metrics 
                if m.timestamp >= cutoff_time
            ]
        
        if not recent_metrics:
            return {
                "success_rate": 0.0,
                "avg_completeness_score": 0.0,
                "total_processed": 0,
                "avg_processing_time_ms": 0.0
            }
        
        successful = sum(1 for m in recent_metrics if m.success)
        total_completeness = sum(m.data_completeness_score for m in recent_metrics)
        total_processing_time = sum(m.total_processing_time_ms for m in recent_metrics)
        
        return {
            "success_rate": successful / len(recent_metrics),
            "avg_completeness_score": total_completeness / len(recent_metrics),
            "total_processed": len(recent_metrics),
            "avg_processing_time_ms": total_processing_time / len(recent_metrics)
        }
    
    async def get_recent_alerts(
        self,
        time_window_hours: int = 24,
        severity_filter: Optional[AlertSeverity] = None
    ) -> List[PreferenceAlert]:
        """Get recent alerts within time window, optionally filtered by severity"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        async with self._lock:
            recent_alerts = [
                alert for alert in self._alerts 
                if alert.timestamp >= cutoff_time
            ]
        
        if severity_filter:
            recent_alerts = [
                alert for alert in recent_alerts 
                if alert.severity == severity_filter
            ]
            
        return sorted(recent_alerts, key=lambda x: x.timestamp, reverse=True)
    
    async def export_metrics_summary(self) -> Dict[str, Any]:
        """Export comprehensive metrics summary"""
        
        query_rates = await self.get_query_success_rates()
        document_rates = await self.get_document_creation_rates()
        recent_alerts = await self.get_recent_alerts()
        
        return {
            "query_success_rates": query_rates,
            "document_creation_metrics": document_rates,
            "recent_alerts": [
                {
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "affected_users_count": len(alert.affected_users),
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in recent_alerts
            ],
            "summary": {
                "overall_query_success_rate": sum(query_rates.values()) / len(query_rates) if query_rates else 0.0,
                "document_success_rate": document_rates.get("success_rate", 0.0),
                "avg_data_completeness": document_rates.get("avg_completeness_score", 0.0),
                "critical_alerts_count": len([a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL])
            }
        }

# Global instance
_preference_metrics_collector = None

def get_preference_metrics_collector() -> PreferenceMetricsCollector:
    """Get global preference metrics collector instance"""
    global _preference_metrics_collector
    if _preference_metrics_collector is None:
        _preference_metrics_collector = PreferenceMetricsCollector()
    return _preference_metrics_collector