"""
Enhanced Preference Data Diagnostics Module

This module provides advanced diagnostic capabilities for preference data analysis,
including bulk analysis, pattern detection, and administrative tools.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

from database.connection import db_manager
from etl.legacy_query_executor import (
    AptitudeTestQueries, 
    PreferenceDataReport, 
    PreferenceQueryDiagnostics
)

logger = logging.getLogger(__name__)


@dataclass
class BulkAnalysisResult:
    """Result of bulk preference data analysis"""
    analysis_id: str
    start_anp_seq: int
    end_anp_seq: int
    total_users: int
    analyzed_users: int
    successful_users: int
    failed_users: int
    analysis_duration: float
    query_success_rates: Dict[str, float]
    data_availability_rates: Dict[str, float]
    performance_metrics: Dict[str, Dict[str, float]]
    failure_patterns: Dict[str, int]
    data_quality_distribution: Dict[str, List[float]]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PreferenceDataPattern:
    """Identified pattern in preference data"""
    pattern_type: str  # "failure", "performance", "quality", "availability"
    pattern_name: str
    affected_queries: List[str]
    affected_users: List[int]
    severity: str  # "low", "medium", "high", "critical"
    description: str
    recommended_actions: List[str]
    confidence_score: float


@dataclass
class AdminDiagnosticSummary:
    """Administrative summary of preference data health"""
    total_users_checked: int
    overall_health_score: float
    critical_issues: List[PreferenceDataPattern]
    warning_issues: List[PreferenceDataPattern]
    performance_summary: Dict[str, float]
    data_availability_summary: Dict[str, float]
    trending_issues: List[str]
    system_recommendations: List[str]
    last_updated: datetime = field(default_factory=datetime.now)


class PreferenceBulkAnalyzer:
    """
    Advanced bulk analyzer for preference data across multiple users
    """
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.session = None
        
    async def initialize(self):
        """Initialize database connection"""
        self.session = db_manager.get_sync_session()
        
    def cleanup(self):
        """Clean up resources"""
        if self.session:
            self.session.close()
    
    def analyze_user_range(
        self, 
        start_anp_seq: int, 
        end_anp_seq: int,
        sample_size: Optional[int] = None,
        parallel: bool = True
    ) -> BulkAnalysisResult:
        """
        Analyze preference data for a range of users
        
        Args:
            start_anp_seq: Starting user sequence number
            end_anp_seq: Ending user sequence number (inclusive)
            sample_size: If provided, randomly sample this many users from the range
            parallel: Whether to use parallel processing
            
        Returns:
            BulkAnalysisResult with comprehensive analysis
        """
        analysis_start = time.time()
        analysis_id = f"bulk_{start_anp_seq}_{end_anp_seq}_{int(time.time())}"
        
        logger.info(f"Starting bulk analysis {analysis_id} for range {start_anp_seq}-{end_anp_seq}")
        
        # Determine user list
        user_list = list(range(start_anp_seq, end_anp_seq + 1))
        if sample_size and sample_size < len(user_list):
            import random
            user_list = random.sample(user_list, sample_size)
            logger.info(f"Sampling {sample_size} users from range")
        
        # Analyze users
        if parallel and len(user_list) > 10:
            reports = self._analyze_users_parallel(user_list)
        else:
            reports = self._analyze_users_sequential(user_list)
        
        # Process results
        analysis_duration = time.time() - analysis_start
        
        result = self._process_bulk_results(
            analysis_id=analysis_id,
            start_anp_seq=start_anp_seq,
            end_anp_seq=end_anp_seq,
            user_list=user_list,
            reports=reports,
            analysis_duration=analysis_duration
        )
        
        logger.info(
            f"Bulk analysis {analysis_id} completed: "
            f"{result.successful_users}/{result.analyzed_users} users successful "
            f"in {analysis_duration:.2f}s"
        )
        
        return result
    
    def _analyze_users_parallel(self, user_list: List[int]) -> List[PreferenceDataReport]:
        """Analyze users in parallel using thread pool"""
        reports = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_anp_seq = {
                executor.submit(self._analyze_single_user, anp_seq): anp_seq 
                for anp_seq in user_list
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_anp_seq):
                anp_seq = future_to_anp_seq[future]
                try:
                    report = future.result()
                    reports.append(report)
                    
                    # Progress logging
                    if len(reports) % 10 == 0:
                        progress = (len(reports) / len(user_list)) * 100
                        logger.info(f"Parallel analysis progress: {progress:.1f}% ({len(reports)}/{len(user_list)})")
                        
                except Exception as e:
                    logger.error(f"Failed to analyze anp_seq {anp_seq}: {e}")
                    # Create failure report
                    reports.append(self._create_failure_report(anp_seq, str(e)))
        
        return reports
    
    def _analyze_users_sequential(self, user_list: List[int]) -> List[PreferenceDataReport]:
        """Analyze users sequentially"""
        reports = []
        
        for i, anp_seq in enumerate(user_list):
            try:
                report = self._analyze_single_user(anp_seq)
                reports.append(report)
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    progress = ((i + 1) / len(user_list)) * 100
                    logger.info(f"Sequential analysis progress: {progress:.1f}% ({i + 1}/{len(user_list)})")
                    
            except Exception as e:
                logger.error(f"Failed to analyze anp_seq {anp_seq}: {e}")
                reports.append(self._create_failure_report(anp_seq, str(e)))
        
        return reports
    
    def _analyze_single_user(self, anp_seq: int) -> PreferenceDataReport:
        """Analyze preference data for a single user"""
        queries = AptitudeTestQueries(self.session)
        return queries.diagnose_preference_queries(anp_seq)
    
    def _create_failure_report(self, anp_seq: int, error_message: str) -> PreferenceDataReport:
        """Create a failure report for a user that couldn't be analyzed"""
        return PreferenceDataReport(
            anp_seq=anp_seq,
            total_queries=3,
            successful_queries=0,
            failed_queries=3,
            total_execution_time=0.0,
            data_availability={
                "imagePreferenceStatsQuery": False,
                "preferenceDataQuery": False,
                "preferenceJobsQuery": False
            },
            diagnostics=[],
            recommendations=[f"Analysis failed: {error_message}"]
        )
    
    def _process_bulk_results(
        self,
        analysis_id: str,
        start_anp_seq: int,
        end_anp_seq: int,
        user_list: List[int],
        reports: List[PreferenceDataReport],
        analysis_duration: float
    ) -> BulkAnalysisResult:
        """Process bulk analysis results into summary statistics"""
        
        total_users = len(user_list)
        analyzed_users = len(reports)
        successful_users = sum(1 for r in reports if r.successful_queries == r.total_queries)
        failed_users = analyzed_users - successful_users
        
        # Calculate query success rates
        query_success_counts = defaultdict(int)
        query_total_counts = defaultdict(int)
        data_availability_counts = defaultdict(int)
        
        # Performance metrics
        execution_times_by_query = defaultdict(list)
        
        # Data quality metrics
        quality_scores_by_query = defaultdict(list)
        
        # Failure patterns
        failure_patterns = defaultdict(int)
        
        for report in reports:
            for diagnostic in report.diagnostics:
                query_name = diagnostic.query_name
                query_total_counts[query_name] += 1
                
                if diagnostic.success:
                    query_success_counts[query_name] += 1
                    execution_times_by_query[query_name].append(diagnostic.execution_time)
                    
                    if diagnostic.row_count > 0:
                        data_availability_counts[query_name] += 1
                    
                    if diagnostic.data_quality_score is not None:
                        quality_scores_by_query[query_name].append(diagnostic.data_quality_score)
                else:
                    # Track failure patterns
                    if diagnostic.error_details:
                        error_type = diagnostic.error_details.split(':')[0]
                        pattern_key = f"{query_name}:{error_type}"
                        failure_patterns[pattern_key] += 1
        
        # Calculate rates
        query_success_rates = {
            query: (query_success_counts[query] / query_total_counts[query]) * 100
            for query in query_total_counts
        }
        
        data_availability_rates = {
            query: (data_availability_counts[query] / query_total_counts[query]) * 100
            for query in query_total_counts
        }
        
        # Calculate performance metrics
        performance_metrics = {}
        for query_name, times in execution_times_by_query.items():
            if times:
                performance_metrics[query_name] = {
                    "avg_time": statistics.mean(times),
                    "median_time": statistics.median(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "std_dev": statistics.stdev(times) if len(times) > 1 else 0.0
                }
        
        # Generate recommendations
        recommendations = self._generate_bulk_recommendations(
            successful_users, total_users, query_success_rates, 
            data_availability_rates, failure_patterns
        )
        
        return BulkAnalysisResult(
            analysis_id=analysis_id,
            start_anp_seq=start_anp_seq,
            end_anp_seq=end_anp_seq,
            total_users=total_users,
            analyzed_users=analyzed_users,
            successful_users=successful_users,
            failed_users=failed_users,
            analysis_duration=analysis_duration,
            query_success_rates=query_success_rates,
            data_availability_rates=data_availability_rates,
            performance_metrics=performance_metrics,
            failure_patterns=dict(failure_patterns),
            data_quality_distribution=dict(quality_scores_by_query),
            recommendations=recommendations
        )
    
    def _generate_bulk_recommendations(
        self,
        successful_users: int,
        total_users: int,
        query_success_rates: Dict[str, float],
        data_availability_rates: Dict[str, float],
        failure_patterns: Dict[str, int]
    ) -> List[str]:
        """Generate recommendations based on bulk analysis results"""
        recommendations = []
        
        success_rate = (successful_users / total_users) * 100 if total_users > 0 else 0
        
        # Overall success rate recommendations
        if success_rate < 50:
            recommendations.append(
                f"CRITICAL: Only {success_rate:.1f}% of users have functional preference queries. "
                "Immediate investigation required."
            )
        elif success_rate < 80:
            recommendations.append(
                f"WARNING: {success_rate:.1f}% success rate indicates systemic issues. "
                "Review database connectivity and query performance."
            )
        
        # Query-specific recommendations
        for query_name, success_rate in query_success_rates.items():
            if success_rate < 50:
                recommendations.append(
                    f"CRITICAL: {query_name} failing for {100-success_rate:.1f}% of users. "
                    "Check query syntax and database schema."
                )
            
            data_rate = data_availability_rates.get(query_name, 0)
            if success_rate > 80 and data_rate < 30:
                recommendations.append(
                    f"WARNING: {query_name} executes successfully but returns no data for "
                    f"{100-data_rate:.1f}% of users. Review data migration completeness."
                )
        
        # Failure pattern recommendations
        if failure_patterns:
            most_common_failure = max(failure_patterns.items(), key=lambda x: x[1])
            pattern, count = most_common_failure
            
            if count > total_users * 0.1:  # More than 10% of users affected
                recommendations.append(
                    f"PATTERN DETECTED: '{pattern}' affects {count} users ({count/total_users*100:.1f}%). "
                    "Focus troubleshooting efforts on this specific issue."
                )
            
            # Check for connection issues
            connection_failures = sum(
                count for pattern, count in failure_patterns.items() 
                if "Connection" in pattern or "Timeout" in pattern
            )
            if connection_failures > total_users * 0.05:
                recommendations.append(
                    "WARNING: High number of connection/timeout errors detected. "
                    "Review database connection pool settings and network stability."
                )
        
        return recommendations


class PreferencePatternDetector:
    """
    Detects patterns and anomalies in preference data across users
    """
    
    def __init__(self):
        self.session = None
        
    async def initialize(self):
        """Initialize database connection"""
        self.session = db_manager.get_sync_session()
        
    def cleanup(self):
        """Clean up resources"""
        if self.session:
            self.session.close()
    
    def detect_patterns(self, reports: List[PreferenceDataReport]) -> List[PreferenceDataPattern]:
        """
        Detect patterns in preference data reports
        
        Args:
            reports: List of preference data reports to analyze
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        # Detect failure patterns
        patterns.extend(self._detect_failure_patterns(reports))
        
        # Detect performance patterns
        patterns.extend(self._detect_performance_patterns(reports))
        
        # Detect data quality patterns
        patterns.extend(self._detect_quality_patterns(reports))
        
        # Detect availability patterns
        patterns.extend(self._detect_availability_patterns(reports))
        
        # Sort by severity and confidence
        patterns.sort(key=lambda p: (
            {"critical": 4, "high": 3, "medium": 2, "low": 1}[p.severity],
            p.confidence_score
        ), reverse=True)
        
        return patterns
    
    def _detect_failure_patterns(self, reports: List[PreferenceDataReport]) -> List[PreferenceDataPattern]:
        """Detect systematic failure patterns"""
        patterns = []
        
        # Group failures by error type and query
        failure_groups = defaultdict(lambda: defaultdict(list))
        
        for report in reports:
            for diagnostic in report.diagnostics:
                if not diagnostic.success and diagnostic.error_details:
                    error_type = diagnostic.error_details.split(':')[0]
                    failure_groups[error_type][diagnostic.query_name].append(report.anp_seq)
        
        # Analyze each failure group
        for error_type, query_failures in failure_groups.items():
            for query_name, affected_users in query_failures.items():
                if len(affected_users) >= 5:  # At least 5 users affected
                    severity = self._calculate_failure_severity(len(affected_users), len(reports))
                    confidence = min(0.9, len(affected_users) / 10)  # Higher confidence with more occurrences
                    
                    patterns.append(PreferenceDataPattern(
                        pattern_type="failure",
                        pattern_name=f"Systematic {error_type} in {query_name}",
                        affected_queries=[query_name],
                        affected_users=affected_users,
                        severity=severity,
                        description=f"{error_type} error affecting {len(affected_users)} users in {query_name}",
                        recommended_actions=[
                            f"Investigate {error_type} root cause in {query_name}",
                            "Check database connectivity and query syntax",
                            "Review error logs for additional context"
                        ],
                        confidence_score=confidence
                    ))
        
        return patterns
    
    def _detect_performance_patterns(self, reports: List[PreferenceDataReport]) -> List[PreferenceDataPattern]:
        """Detect performance-related patterns"""
        patterns = []
        
        # Collect execution times by query
        execution_times_by_query = defaultdict(list)
        
        for report in reports:
            for diagnostic in report.diagnostics:
                if diagnostic.success:
                    execution_times_by_query[diagnostic.query_name].append(
                        (diagnostic.execution_time, report.anp_seq)
                    )
        
        # Analyze performance patterns
        for query_name, time_data in execution_times_by_query.items():
            if len(time_data) < 5:
                continue
                
            times = [t[0] for t in time_data]
            avg_time = statistics.mean(times)
            
            # Detect slow queries
            if avg_time > 3.0:  # Queries taking more than 3 seconds on average
                slow_users = [anp_seq for time, anp_seq in time_data if time > avg_time * 1.5]
                
                patterns.append(PreferenceDataPattern(
                    pattern_type="performance",
                    pattern_name=f"Slow execution in {query_name}",
                    affected_queries=[query_name],
                    affected_users=slow_users,
                    severity="medium" if avg_time < 6 else "high",
                    description=f"{query_name} has average execution time of {avg_time:.2f}s",
                    recommended_actions=[
                        f"Optimize {query_name} SQL query",
                        "Check database indexes and query plan",
                        "Consider query result caching"
                    ],
                    confidence_score=0.8
                ))
            
            # Detect highly variable performance
            if len(times) > 1:
                std_dev = statistics.stdev(times)
                if std_dev > avg_time * 0.5:  # High variability
                    patterns.append(PreferenceDataPattern(
                        pattern_type="performance",
                        pattern_name=f"Variable performance in {query_name}",
                        affected_queries=[query_name],
                        affected_users=[anp_seq for _, anp_seq in time_data],
                        severity="medium",
                        description=f"{query_name} has high performance variability (std dev: {std_dev:.2f}s)",
                        recommended_actions=[
                            "Investigate performance inconsistencies",
                            "Check for database load patterns",
                            "Review connection pool configuration"
                        ],
                        confidence_score=0.7
                    ))
        
        return patterns
    
    def _detect_quality_patterns(self, reports: List[PreferenceDataReport]) -> List[PreferenceDataPattern]:
        """Detect data quality patterns"""
        patterns = []
        
        # Collect quality scores by query
        quality_scores_by_query = defaultdict(list)
        
        for report in reports:
            for diagnostic in report.diagnostics:
                if diagnostic.success and diagnostic.data_quality_score is not None:
                    quality_scores_by_query[diagnostic.query_name].append(
                        (diagnostic.data_quality_score, report.anp_seq)
                    )
        
        # Analyze quality patterns
        for query_name, score_data in quality_scores_by_query.items():
            if len(score_data) < 5:
                continue
                
            scores = [s[0] for s in score_data]
            avg_score = statistics.mean(scores)
            
            # Detect low quality data
            if avg_score < 0.5:
                low_quality_users = [anp_seq for score, anp_seq in score_data if score < 0.3]
                
                patterns.append(PreferenceDataPattern(
                    pattern_type="quality",
                    pattern_name=f"Low data quality in {query_name}",
                    affected_queries=[query_name],
                    affected_users=low_quality_users,
                    severity="high" if avg_score < 0.3 else "medium",
                    description=f"{query_name} has average quality score of {avg_score:.2f}",
                    recommended_actions=[
                        f"Review data validation rules for {query_name}",
                        "Check source data integrity",
                        "Implement data quality monitoring"
                    ],
                    confidence_score=0.9
                ))
        
        return patterns
    
    def _detect_availability_patterns(self, reports: List[PreferenceDataReport]) -> List[PreferenceDataPattern]:
        """Detect data availability patterns"""
        patterns = []
        
        # Count data availability by query
        availability_by_query = defaultdict(lambda: {"total": 0, "available": 0, "users": []})
        
        for report in reports:
            for query_name, available in report.data_availability.items():
                availability_by_query[query_name]["total"] += 1
                if available:
                    availability_by_query[query_name]["available"] += 1
                else:
                    availability_by_query[query_name]["users"].append(report.anp_seq)
        
        # Analyze availability patterns
        for query_name, stats in availability_by_query.items():
            if stats["total"] < 5:
                continue
                
            availability_rate = (stats["available"] / stats["total"]) * 100
            
            if availability_rate < 50:  # Less than 50% data availability
                patterns.append(PreferenceDataPattern(
                    pattern_type="availability",
                    pattern_name=f"Low data availability in {query_name}",
                    affected_queries=[query_name],
                    affected_users=stats["users"],
                    severity="critical" if availability_rate < 25 else "high",
                    description=f"{query_name} has only {availability_rate:.1f}% data availability",
                    recommended_actions=[
                        f"Investigate missing data for {query_name}",
                        "Check ETL pipeline completeness",
                        "Review data migration processes"
                    ],
                    confidence_score=0.95
                ))
        
        return patterns
    
    def _calculate_failure_severity(self, affected_count: int, total_count: int) -> str:
        """Calculate severity based on affected user percentage"""
        percentage = (affected_count / total_count) * 100
        
        if percentage >= 50:
            return "critical"
        elif percentage >= 25:
            return "high"
        elif percentage >= 10:
            return "medium"
        else:
            return "low"


class AdminPreferenceDashboard:
    """
    Administrative dashboard for preference data health monitoring
    """
    
    def __init__(self):
        self.bulk_analyzer = PreferenceBulkAnalyzer()
        self.pattern_detector = PreferencePatternDetector()
        
    async def initialize(self):
        """Initialize all components"""
        await self.bulk_analyzer.initialize()
        await self.pattern_detector.initialize()
        
    def cleanup(self):
        """Clean up all components"""
        self.bulk_analyzer.cleanup()
        self.pattern_detector.cleanup()
    
    async def generate_health_summary(
        self, 
        sample_size: int = 100,
        anp_seq_range: Optional[Tuple[int, int]] = None
    ) -> AdminDiagnosticSummary:
        """
        Generate comprehensive health summary for preference data
        
        Args:
            sample_size: Number of users to sample for analysis
            anp_seq_range: Optional range to sample from (start, end)
            
        Returns:
            AdminDiagnosticSummary with system health information
        """
        logger.info(f"Generating admin health summary with sample size {sample_size}")
        
        # Determine sampling range
        if anp_seq_range:
            start_anp_seq, end_anp_seq = anp_seq_range
        else:
            # Use a reasonable default range (last 10000 users)
            start_anp_seq = 10000
            end_anp_seq = 20000
        
        # Run bulk analysis
        bulk_result = self.bulk_analyzer.analyze_user_range(
            start_anp_seq=start_anp_seq,
            end_anp_seq=end_anp_seq,
            sample_size=sample_size,
            parallel=True
        )
        
        # Collect individual reports for pattern detection
        reports = []
        for anp_seq in range(start_anp_seq, min(start_anp_seq + sample_size, end_anp_seq + 1)):
            try:
                queries = AptitudeTestQueries(self.bulk_analyzer.session)
                report = queries.diagnose_preference_queries(anp_seq)
                reports.append(report)
            except Exception as e:
                logger.warning(f"Failed to get detailed report for anp_seq {anp_seq}: {e}")
        
        # Detect patterns
        patterns = self.pattern_detector.detect_patterns(reports)
        
        # Categorize patterns by severity
        critical_issues = [p for p in patterns if p.severity == "critical"]
        warning_issues = [p for p in patterns if p.severity in ["high", "medium"]]
        
        # Calculate overall health score
        health_score = self._calculate_health_score(bulk_result, patterns)
        
        # Generate trending issues
        trending_issues = self._identify_trending_issues(patterns)
        
        # Generate system recommendations
        system_recommendations = self._generate_system_recommendations(
            bulk_result, critical_issues, warning_issues
        )
        
        return AdminDiagnosticSummary(
            total_users_checked=bulk_result.analyzed_users,
            overall_health_score=health_score,
            critical_issues=critical_issues,
            warning_issues=warning_issues,
            performance_summary=self._summarize_performance(bulk_result),
            data_availability_summary=bulk_result.data_availability_rates,
            trending_issues=trending_issues,
            system_recommendations=system_recommendations
        )
    
    def _calculate_health_score(
        self, 
        bulk_result: BulkAnalysisResult, 
        patterns: List[PreferenceDataPattern]
    ) -> float:
        """Calculate overall system health score (0-100)"""
        base_score = 100.0
        
        # Deduct points for low success rates
        success_rate = (bulk_result.successful_users / bulk_result.analyzed_users) * 100
        if success_rate < 90:
            base_score -= (90 - success_rate) * 0.5
        
        # Deduct points for critical issues
        critical_count = len([p for p in patterns if p.severity == "critical"])
        base_score -= critical_count * 15
        
        # Deduct points for high/medium issues
        high_count = len([p for p in patterns if p.severity == "high"])
        medium_count = len([p for p in patterns if p.severity == "medium"])
        base_score -= high_count * 8
        base_score -= medium_count * 3
        
        # Deduct points for poor data availability
        avg_availability = statistics.mean(bulk_result.data_availability_rates.values())
        if avg_availability < 80:
            base_score -= (80 - avg_availability) * 0.3
        
        return max(0.0, min(100.0, base_score))
    
    def _summarize_performance(self, bulk_result: BulkAnalysisResult) -> Dict[str, float]:
        """Summarize performance metrics"""
        summary = {}
        
        for query_name, metrics in bulk_result.performance_metrics.items():
            summary[f"{query_name}_avg_time"] = metrics["avg_time"]
            summary[f"{query_name}_max_time"] = metrics["max_time"]
        
        # Overall performance score
        avg_times = [metrics["avg_time"] for metrics in bulk_result.performance_metrics.values()]
        if avg_times:
            summary["overall_avg_time"] = statistics.mean(avg_times)
            summary["performance_score"] = max(0, 100 - (summary["overall_avg_time"] * 10))
        
        return summary
    
    def _identify_trending_issues(self, patterns: List[PreferenceDataPattern]) -> List[str]:
        """Identify trending issues from patterns"""
        trending = []
        
        # Group patterns by type
        pattern_types = defaultdict(int)
        for pattern in patterns:
            pattern_types[pattern.pattern_type] += 1
        
        # Identify trends
        if pattern_types["failure"] >= 2:
            trending.append("Increasing failure rates across multiple queries")
        
        if pattern_types["performance"] >= 1:
            trending.append("Performance degradation detected")
        
        if pattern_types["availability"] >= 1:
            trending.append("Data availability issues identified")
        
        return trending
    
    def _generate_system_recommendations(
        self,
        bulk_result: BulkAnalysisResult,
        critical_issues: List[PreferenceDataPattern],
        warning_issues: List[PreferenceDataPattern]
    ) -> List[str]:
        """Generate system-level recommendations"""
        recommendations = []
        
        # Critical issue recommendations
        if critical_issues:
            recommendations.append(
                f"URGENT: {len(critical_issues)} critical issues detected. "
                "Immediate attention required to prevent system degradation."
            )
        
        # Success rate recommendations
        success_rate = (bulk_result.successful_users / bulk_result.analyzed_users) * 100
        if success_rate < 80:
            recommendations.append(
                "System success rate below acceptable threshold. "
                "Review database connectivity and query reliability."
            )
        
        # Performance recommendations
        avg_times = [
            metrics["avg_time"] 
            for metrics in bulk_result.performance_metrics.values()
        ]
        if avg_times and statistics.mean(avg_times) > 3.0:
            recommendations.append(
                "Query performance degradation detected. "
                "Consider database optimization and indexing review."
            )
        
        # Data availability recommendations
        low_availability_queries = [
            query for query, rate in bulk_result.data_availability_rates.items()
            if rate < 70
        ]
        if low_availability_queries:
            recommendations.append(
                f"Low data availability in {', '.join(low_availability_queries)}. "
                "Review ETL pipeline and data migration processes."
            )
        
        return recommendations


class PreferenceDiagnostics:
    """
    Enhanced preference diagnostics with repair capabilities for administrative tools.
    """
    
    def __init__(self):
        self.session = None
        
    async def initialize(self):
        """Initialize database connection"""
        from database.connection import db_manager
        self.session = await db_manager.get_async_session().__aenter__()
        
    def cleanup(self):
        """Clean up resources"""
        if self.session:
            self.session.close()

    async def diagnose_user_preference_data(self, anp_seq: int) -> Dict[str, Any]:
        """
        Comprehensive diagnostic for a specific user's preference data.
        """
        diagnostic_info = {
            "anp_seq": anp_seq,
            "timestamp": datetime.now().isoformat(),
            "query_status": {},
            "validation_results": {},
            "issues": [],
            "recommendations": []
        }
        
        try:
            from etl.legacy_query_executor import LegacyQueryExecutor
            from etl.preference_data_validator import PreferenceDataValidator
            
            # Test each preference query
            query_executor = LegacyQueryExecutor()
            
            # Test image preference stats query
            try:
                stats_result = await query_executor.imagePreferenceStatsQuery(anp_seq)
                diagnostic_info["query_status"]["imagePreferenceStatsQuery"] = {
                    "success": True,
                    "row_count": len(stats_result) if stats_result else 0,
                    "has_data": bool(stats_result)
                }
            except Exception as e:
                diagnostic_info["query_status"]["imagePreferenceStatsQuery"] = {
                    "success": False,
                    "error": str(e)
                }
                diagnostic_info["issues"].append(f"Image preference stats query failed: {str(e)}")
            
            # Test preference data query
            try:
                pref_result = await query_executor.preferenceDataQuery(anp_seq)
                diagnostic_info["query_status"]["preferenceDataQuery"] = {
                    "success": True,
                    "row_count": len(pref_result) if pref_result else 0,
                    "has_data": bool(pref_result)
                }
            except Exception as e:
                diagnostic_info["query_status"]["preferenceDataQuery"] = {
                    "success": False,
                    "error": str(e)
                }
                diagnostic_info["issues"].append(f"Preference data query failed: {str(e)}")
            
            # Test preference jobs query
            try:
                jobs_result = await query_executor.preferenceJobsQuery(anp_seq)
                diagnostic_info["query_status"]["preferenceJobsQuery"] = {
                    "success": True,
                    "row_count": len(jobs_result) if jobs_result else 0,
                    "has_data": bool(jobs_result)
                }
            except Exception as e:
                diagnostic_info["query_status"]["preferenceJobsQuery"] = {
                    "success": False,
                    "error": str(e)
                }
                diagnostic_info["issues"].append(f"Preference jobs query failed: {str(e)}")
            
            # Validate data if queries succeeded
            validator = PreferenceDataValidator()
            
            if diagnostic_info["query_status"].get("imagePreferenceStatsQuery", {}).get("success"):
                try:
                    stats_validation = await validator.validate_image_preference_stats(stats_result)
                    diagnostic_info["validation_results"]["imagePreferenceStats"] = stats_validation
                    if not stats_validation.get("is_valid", False):
                        diagnostic_info["issues"].extend(stats_validation.get("issues", []))
                except Exception as e:
                    diagnostic_info["issues"].append(f"Image preference stats validation failed: {str(e)}")
            
            if diagnostic_info["query_status"].get("preferenceDataQuery", {}).get("success"):
                try:
                    pref_validation = await validator.validate_preference_data(pref_result)
                    diagnostic_info["validation_results"]["preferenceData"] = pref_validation
                    if not pref_validation.get("is_valid", False):
                        diagnostic_info["issues"].extend(pref_validation.get("issues", []))
                except Exception as e:
                    diagnostic_info["issues"].append(f"Preference data validation failed: {str(e)}")
            
            if diagnostic_info["query_status"].get("preferenceJobsQuery", {}).get("success"):
                try:
                    jobs_validation = await validator.validate_preference_jobs(jobs_result)
                    diagnostic_info["validation_results"]["preferenceJobs"] = jobs_validation
                    if not jobs_validation.get("is_valid", False):
                        diagnostic_info["issues"].extend(jobs_validation.get("issues", []))
                except Exception as e:
                    diagnostic_info["issues"].append(f"Preference jobs validation failed: {str(e)}")
            
            # Generate recommendations
            self._generate_recommendations(diagnostic_info)
            
            return diagnostic_info
            
        except Exception as e:
            logger.error(f"Error in user preference diagnostic for anp_seq {anp_seq}: {str(e)}")
            diagnostic_info["issues"].append(f"Diagnostic process failed: {str(e)}")
            return diagnostic_info

    async def repair_user_preference_data(self, anp_seq: int) -> Dict[str, Any]:
        """
        Attempt to repair preference data for a specific user by re-processing their data.
        """
        repair_result = {
            "anp_seq": anp_seq,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "documents_created": 0,
            "error": None,
            "steps_completed": []
        }
        
        try:
            from etl.document_transformer import DocumentTransformer
            from database.connection import db_manager
            from database.repositories import DocumentRepository
            from etl.legacy_query_executor import LegacyQueryExecutor
            
            # Get database session
            async with db_manager.get_async_session() as db_session:
                doc_repo = DocumentRepository(db_session)
                transformer = DocumentTransformer()
                
                # Step 1: Remove existing preference documents
                try:
                    existing_docs = await doc_repo.get_documents_by_anp_seq(anp_seq)
                    preference_docs = [doc for doc in existing_docs if doc.document_type == "PREFERENCE_ANALYSIS"]
                    
                    for doc in preference_docs:
                        await doc_repo.delete_document(doc.id)
                    
                    repair_result["steps_completed"].append(f"Removed {len(preference_docs)} existing preference documents")
                    
                except Exception as e:
                    logger.warning(f"Failed to remove existing preference documents for anp_seq {anp_seq}: {str(e)}")
                
                # Step 2: Re-execute preference queries and create new documents
                try:
                    query_executor = LegacyQueryExecutor()
                    
                    # Execute all preference queries
                    stats_result = await query_executor.imagePreferenceStatsQuery(anp_seq)
                    pref_result = await query_executor.preferenceDataQuery(anp_seq)
                    jobs_result = await query_executor.preferenceJobsQuery(anp_seq)
                    
                    repair_result["steps_completed"].append("Re-executed preference queries")
                    
                    # Transform data into documents
                    query_results = {
                        "imagePreferenceStatsQuery": stats_result,
                        "preferenceDataQuery": pref_result,
                        "preferenceJobsQuery": jobs_result
                    }
                    
                    # Use the enhanced document transformer
                    preference_documents = await transformer._chunk_preference_analysis(anp_seq, query_results)
                    
                    # Save new documents
                    documents_created = 0
                    for doc in preference_documents:
                        await doc_repo.save_document(doc)
                        documents_created += 1
                    
                    repair_result["documents_created"] = documents_created
                    repair_result["steps_completed"].append(f"Created {documents_created} new preference documents")
                    
                    # Step 3: Validate the repair
                    if documents_created > 0:
                        from etl.preference_data_validator import PreferenceDataValidator
                        validator = PreferenceDataValidator()
                        validation_result = await validator.validate_user_preference_data(anp_seq)
                        
                        if validation_result.get("is_valid", False):
                            repair_result["success"] = True
                            repair_result["steps_completed"].append("Validation passed - repair successful")
                        else:
                            repair_result["error"] = "Repair completed but validation failed"
                            repair_result["steps_completed"].append("Validation failed after repair")
                    else:
                        repair_result["error"] = "No preference documents were created during repair"
                        repair_result["steps_completed"].append("No documents created - repair failed")
                
                except Exception as e:
                    repair_result["error"] = f"Failed to re-process preference data: {str(e)}"
                    logger.error(f"Preference data repair failed for anp_seq {anp_seq}: {str(e)}")
            
            return repair_result
            
        except Exception as e:
            repair_result["error"] = f"Repair process failed: {str(e)}"
            logger.error(f"Error in preference data repair for anp_seq {anp_seq}: {str(e)}")
            return repair_result

    def _generate_recommendations(self, diagnostic_info: Dict[str, Any]):
        """Generate recommendations based on diagnostic results"""
        recommendations = []
        
        # Check for query failures
        failed_queries = []
        for query_name, status in diagnostic_info["query_status"].items():
            if not status.get("success", False):
                failed_queries.append(query_name)
        
        if failed_queries:
            recommendations.append(f"Fix query execution issues for: {', '.join(failed_queries)}")
        
        # Check for empty results
        empty_queries = []
        for query_name, status in diagnostic_info["query_status"].items():
            if status.get("success", False) and not status.get("has_data", False):
                empty_queries.append(query_name)
        
        if empty_queries:
            recommendations.append(f"Investigate missing data for: {', '.join(empty_queries)}")
        
        # Check for validation issues
        if diagnostic_info["validation_results"]:
            invalid_data = []
            for data_type, validation in diagnostic_info["validation_results"].items():
                if not validation.get("is_valid", False):
                    invalid_data.append(data_type)
            
            if invalid_data:
                recommendations.append(f"Fix data quality issues for: {', '.join(invalid_data)}")
        
        # General recommendations
        if not diagnostic_info["issues"]:
            recommendations.append("All preference queries are functioning correctly")
        else:
            recommendations.append("Consider running repair process to fix identified issues")
        
        diagnostic_info["recommendations"] = recommendations