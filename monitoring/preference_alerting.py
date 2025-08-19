"""
Preference Data Processing Alerting System

Monitors preference processing metrics and generates alerts based on configurable rules.
Provides automated reporting for users affected by preference data problems.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from monitoring.preference_metrics import (
    PreferenceMetricsCollector, 
    PreferenceAlert, 
    AlertSeverity,
    get_preference_metrics_collector
)

logger = logging.getLogger(__name__)

@dataclass
class AlertRule:
    """Configuration for an alerting rule"""
    name: str
    description: str
    severity: AlertSeverity
    condition_func: Callable[[Dict[str, Any]], bool]
    message_template: str
    check_interval_minutes: int = 5
    enabled: bool = True

@dataclass
class UserImpactReport:
    """Report of users affected by preference data issues"""
    anp_seq: int
    user_id: Optional[str]
    issues: List[str]
    missing_queries: List[str]
    data_completeness_score: float
    last_processing_attempt: datetime
    recommended_actions: List[str]

class PreferenceAlertingSystem:
    """Manages alerting rules and automated reporting for preference data processing"""
    
    def __init__(self, metrics_collector: Optional[PreferenceMetricsCollector] = None):
        self.metrics_collector = metrics_collector or get_preference_metrics_collector()
        self.alert_rules: List[AlertRule] = []
        self.user_impact_reports: Dict[int, UserImpactReport] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Initialize default alert rules
        self._setup_default_alert_rules()
    
    def _setup_default_alert_rules(self) -> None:
        """Setup default alerting rules for preference processing"""
        
        # Critical: Query success rate below 50%
        self.alert_rules.append(AlertRule(
            name="preference_query_critical_failure",
            description="Preference query success rate critically low",
            severity=AlertSeverity.CRITICAL,
            condition_func=lambda metrics: (
                metrics.get("summary", {}).get("overall_query_success_rate", 0.0) < 0.5
            ),
            message_template="Preference query success rate is {overall_query_success_rate:.1%}, below critical threshold of 50%",
            check_interval_minutes=2
        ))
        
        # Warning: Query success rate below 80%
        self.alert_rules.append(AlertRule(
            name="preference_query_degraded",
            description="Preference query success rate degraded",
            severity=AlertSeverity.WARNING,
            condition_func=lambda metrics: (
                0.5 <= metrics.get("summary", {}).get("overall_query_success_rate", 0.0) < 0.8
            ),
            message_template="Preference query success rate is {overall_query_success_rate:.1%}, below target of 80%",
            check_interval_minutes=5
        ))
        
        # Critical: Document creation success rate below 70%
        self.alert_rules.append(AlertRule(
            name="preference_document_critical_failure",
            description="Preference document creation critically low",
            severity=AlertSeverity.CRITICAL,
            condition_func=lambda metrics: (
                metrics.get("document_creation_metrics", {}).get("success_rate", 0.0) < 0.7
            ),
            message_template="Preference document creation success rate is {success_rate:.1%}, below critical threshold of 70%",
            check_interval_minutes=2
        ))
        
        # Warning: Data completeness below 60%
        self.alert_rules.append(AlertRule(
            name="preference_data_completeness_low",
            description="Preference data completeness degraded",
            severity=AlertSeverity.WARNING,
            condition_func=lambda metrics: (
                metrics.get("summary", {}).get("avg_data_completeness", 0.0) < 0.6
            ),
            message_template="Average preference data completeness is {avg_data_completeness:.1%}, below target of 60%",
            check_interval_minutes=10
        ))
        
        # Critical: No preference processing in last hour
        self.alert_rules.append(AlertRule(
            name="preference_processing_stalled",
            description="No preference processing activity detected",
            severity=AlertSeverity.CRITICAL,
            condition_func=lambda metrics: (
                metrics.get("document_creation_metrics", {}).get("total_processed", 0) == 0
            ),
            message_template="No preference processing activity detected in the last hour",
            check_interval_minutes=15
        ))
        
        # Warning: High processing time
        self.alert_rules.append(AlertRule(
            name="preference_processing_slow",
            description="Preference processing time elevated",
            severity=AlertSeverity.WARNING,
            condition_func=lambda metrics: (
                metrics.get("document_creation_metrics", {}).get("avg_processing_time_ms", 0.0) > 30000  # 30 seconds
            ),
            message_template="Average preference processing time is {avg_processing_time_ms:.0f}ms, above target of 30000ms",
            check_interval_minutes=10
        ))
    
    async def add_alert_rule(self, rule: AlertRule) -> None:
        """Add a custom alert rule"""
        async with self._lock:
            self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")
    
    async def remove_alert_rule(self, rule_name: str) -> bool:
        """Remove an alert rule by name"""
        async with self._lock:
            original_count = len(self.alert_rules)
            self.alert_rules = [rule for rule in self.alert_rules if rule.name != rule_name]
            removed = len(self.alert_rules) < original_count
        
        if removed:
            logger.info(f"Removed alert rule: {rule_name}")
        return removed
    
    async def check_alert_rules(self) -> List[PreferenceAlert]:
        """Check all alert rules and generate alerts for triggered conditions"""
        
        # Get current metrics
        metrics = await self.metrics_collector.export_metrics_summary()
        triggered_alerts = []
        
        async with self._lock:
            active_rules = [rule for rule in self.alert_rules if rule.enabled]
        
        for rule in active_rules:
            try:
                if rule.condition_func(metrics):
                    # Format message with metrics values
                    format_data = {
                        **metrics.get("summary", {}),
                        **metrics.get("document_creation_metrics", {}),
                        **{f"{k}_rate": v for k, v in metrics.get("query_success_rates", {}).items()}
                    }
                    
                    try:
                        message = rule.message_template.format(**format_data)
                    except KeyError as e:
                        # Handle missing format keys gracefully
                        message = f"{rule.description} - formatting error: {e}"
                    
                    alert = await self.metrics_collector.generate_alert(
                        severity=rule.severity,
                        title=rule.description,
                        message=message,
                        metrics={"rule_name": rule.name, "triggered_metrics": metrics}
                    )
                    
                    triggered_alerts.append(alert)
                    
            except Exception as e:
                logger.error(f"Error checking alert rule {rule.name}: {e}")
        
        return triggered_alerts
    
    async def generate_user_impact_report(
        self,
        anp_seq: int,
        query_results: Dict[str, Any],
        document_metrics: Optional[Dict[str, Any]] = None
    ) -> UserImpactReport:
        """Generate impact report for a specific user's preference processing"""
        
        issues = []
        missing_queries = []
        recommended_actions = []
        
        # Analyze query results
        for query_name, result in query_results.items():
            if not result.get("success", False):
                missing_queries.append(query_name)
                issues.append(f"Query {query_name} failed: {result.get('error', 'Unknown error')}")
        
        # Calculate data completeness
        total_queries = len(query_results)
        successful_queries = sum(1 for r in query_results.values() if r.get("success", False))
        data_completeness_score = successful_queries / total_queries if total_queries > 0 else 0.0
        
        # Generate recommendations
        if data_completeness_score < 0.3:
            recommended_actions.append("Critical: Manual investigation required for user data")
            recommended_actions.append("Check legacy database connectivity and user record integrity")
        elif data_completeness_score < 0.7:
            recommended_actions.append("Retry preference processing with enhanced error handling")
            recommended_actions.append("Validate user record exists in legacy system")
        else:
            recommended_actions.append("Monitor for transient issues, may resolve automatically")
        
        if missing_queries:
            recommended_actions.append(f"Focus on resolving queries: {', '.join(missing_queries)}")
        
        report = UserImpactReport(
            anp_seq=anp_seq,
            user_id=None,  # Would need to be provided from context
            issues=issues,
            missing_queries=missing_queries,
            data_completeness_score=data_completeness_score,
            last_processing_attempt=datetime.utcnow(),
            recommended_actions=recommended_actions
        )
        
        async with self._lock:
            self.user_impact_reports[anp_seq] = report
        
        logger.info(
            f"Generated user impact report for anp_seq {anp_seq}",
            extra={
                "data_completeness_score": data_completeness_score,
                "issues_count": len(issues),
                "missing_queries_count": len(missing_queries)
            }
        )
        
        return report
    
    async def get_affected_users_summary(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Get summary of users affected by preference data issues"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        async with self._lock:
            recent_reports = {
                anp_seq: report for anp_seq, report in self.user_impact_reports.items()
                if report.last_processing_attempt >= cutoff_time
            }
        
        if not recent_reports:
            return {
                "total_affected_users": 0,
                "critical_issues": 0,
                "moderate_issues": 0,
                "minor_issues": 0,
                "avg_completeness_score": 0.0,
                "most_common_issues": []
            }
        
        # Categorize by severity
        critical_issues = sum(1 for r in recent_reports.values() if r.data_completeness_score < 0.3)
        moderate_issues = sum(1 for r in recent_reports.values() if 0.3 <= r.data_completeness_score < 0.7)
        minor_issues = sum(1 for r in recent_reports.values() if r.data_completeness_score >= 0.7)
        
        # Calculate average completeness
        avg_completeness = sum(r.data_completeness_score for r in recent_reports.values()) / len(recent_reports)
        
        # Find most common issues
        all_issues = []
        for report in recent_reports.values():
            all_issues.extend(report.issues)
        
        issue_counts = {}
        for issue in all_issues:
            # Extract query name from issue message
            if "Query " in issue and " failed:" in issue:
                query_name = issue.split("Query ")[1].split(" failed:")[0]
                issue_counts[f"Query failure: {query_name}"] = issue_counts.get(f"Query failure: {query_name}", 0) + 1
        
        most_common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_affected_users": len(recent_reports),
            "critical_issues": critical_issues,
            "moderate_issues": moderate_issues,
            "minor_issues": minor_issues,
            "avg_completeness_score": avg_completeness,
            "most_common_issues": most_common_issues
        }
    
    async def start_monitoring(self) -> None:
        """Start continuous monitoring and alerting"""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Monitoring already running")
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started preference alerting monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        logger.info("Stopped preference alerting monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while True:
            try:
                alerts = await self.check_alert_rules()
                if alerts:
                    logger.info(f"Generated {len(alerts)} alerts during monitoring check")
                
                # Wait before next check (use minimum interval from active rules)
                async with self._lock:
                    active_rules = [rule for rule in self.alert_rules if rule.enabled]
                
                if active_rules:
                    min_interval = min(rule.check_interval_minutes for rule in active_rules)
                    await asyncio.sleep(min_interval * 60)
                else:
                    await asyncio.sleep(300)  # Default 5 minutes
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

# Global instance
_preference_alerting_system = None

def get_preference_alerting_system() -> PreferenceAlertingSystem:
    """Get global preference alerting system instance"""
    global _preference_alerting_system
    if _preference_alerting_system is None:
        _preference_alerting_system = PreferenceAlertingSystem()
    return _preference_alerting_system