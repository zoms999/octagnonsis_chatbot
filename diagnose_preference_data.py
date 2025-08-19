#!/usr/bin/env python3
"""
Standalone Preference Data Diagnostic Tool

This script provides comprehensive diagnostic capabilities for preference data analysis,
allowing administrators to test preference queries for specific users and analyze
data availability patterns across multiple anp_seq values.

Usage:
    python diagnose_preference_data.py --anp-seq 12345
    python diagnose_preference_data.py --batch-analyze --start 10000 --end 10100
    python diagnose_preference_data.py --interactive
    python diagnose_preference_data.py --report --output preference_report.json
"""

import asyncio
import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import project modules
from database.connection import db_manager
from etl.legacy_query_executor import (
    AptitudeTestQueries, 
    PreferenceDataReport, 
    PreferenceQueryDiagnostics
)


class PreferenceDataAnalyzer:
    """
    Comprehensive analyzer for preference data across multiple users
    """
    
    def __init__(self):
        self.session = None
        self.queries = None
        
    async def initialize(self):
        """Initialize database connection and query executor"""
        try:
            self.session = db_manager.get_sync_session()
            self.queries = AptitudeTestQueries(self.session)
            logger.info("Preference data analyzer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize analyzer: {e}")
            raise
    
    def cleanup(self):
        """Clean up database connections"""
        if self.session:
            self.session.close()
            logger.info("Database session closed")
    
    def diagnose_single_user(self, anp_seq: int) -> PreferenceDataReport:
        """
        Diagnose preference data for a single user
        
        Args:
            anp_seq: User sequence number
            
        Returns:
            PreferenceDataReport with detailed diagnostic information
        """
        logger.info(f"Starting preference diagnosis for anp_seq: {anp_seq}")
        
        try:
            report = self.queries.diagnose_preference_queries(anp_seq)
            
            # Log summary
            logger.info(
                f"Diagnosis complete for anp_seq {anp_seq}: "
                f"{report.successful_queries}/{report.total_queries} queries successful, "
                f"execution time: {report.total_execution_time:.2f}s"
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to diagnose anp_seq {anp_seq}: {e}")
            # Return a failure report
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
                recommendations=[f"Failed to execute diagnostics: {str(e)}"]
            )
    
    def analyze_batch_users(self, start_anp_seq: int, end_anp_seq: int) -> Dict[str, any]:
        """
        Analyze preference data availability across multiple users
        
        Args:
            start_anp_seq: Starting user sequence number
            end_anp_seq: Ending user sequence number (inclusive)
            
        Returns:
            Dictionary with batch analysis results
        """
        logger.info(f"Starting batch analysis for anp_seq range: {start_anp_seq} to {end_anp_seq}")
        
        batch_start_time = time.time()
        total_users = end_anp_seq - start_anp_seq + 1
        successful_users = 0
        failed_users = 0
        
        # Aggregate statistics
        query_success_rates = {
            "imagePreferenceStatsQuery": 0,
            "preferenceDataQuery": 0,
            "preferenceJobsQuery": 0
        }
        
        data_availability_rates = {
            "imagePreferenceStatsQuery": 0,
            "preferenceDataQuery": 0,
            "preferenceJobsQuery": 0
        }
        
        execution_times = []
        failure_patterns = {}
        user_reports = []
        
        # Process each user
        for anp_seq in range(start_anp_seq, end_anp_seq + 1):
            try:
                report = self.diagnose_single_user(anp_seq)
                user_reports.append(report)
                
                if report.successful_queries > 0:
                    successful_users += 1
                else:
                    failed_users += 1
                
                # Update success rates
                for diagnostic in report.diagnostics:
                    if diagnostic.success:
                        query_success_rates[diagnostic.query_name] += 1
                    
                    # Check data availability (success + has data)
                    if diagnostic.success and diagnostic.row_count > 0:
                        data_availability_rates[diagnostic.query_name] += 1
                
                execution_times.append(report.total_execution_time)
                
                # Track failure patterns
                if report.failed_queries > 0:
                    for diagnostic in report.diagnostics:
                        if not diagnostic.success and diagnostic.error_details:
                            error_type = diagnostic.error_details.split(':')[0]
                            pattern_key = f"{diagnostic.query_name}:{error_type}"
                            failure_patterns[pattern_key] = failure_patterns.get(pattern_key, 0) + 1
                
                # Progress logging
                if anp_seq % 10 == 0:
                    progress = ((anp_seq - start_anp_seq + 1) / total_users) * 100
                    logger.info(f"Batch analysis progress: {progress:.1f}% ({anp_seq - start_anp_seq + 1}/{total_users})")
                    
            except Exception as e:
                logger.error(f"Failed to process anp_seq {anp_seq}: {e}")
                failed_users += 1
        
        batch_execution_time = time.time() - batch_start_time
        
        # Calculate final statistics
        for query_name in query_success_rates:
            query_success_rates[query_name] = (query_success_rates[query_name] / total_users) * 100
            data_availability_rates[query_name] = (data_availability_rates[query_name] / total_users) * 100
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Generate insights and recommendations
        insights = self._generate_batch_insights(
            total_users, successful_users, failed_users,
            query_success_rates, data_availability_rates, failure_patterns
        )
        
        batch_results = {
            "analysis_metadata": {
                "start_anp_seq": start_anp_seq,
                "end_anp_seq": end_anp_seq,
                "total_users": total_users,
                "analysis_time": batch_execution_time,
                "timestamp": datetime.now().isoformat()
            },
            "summary_statistics": {
                "successful_users": successful_users,
                "failed_users": failed_users,
                "success_rate": (successful_users / total_users) * 100,
                "avg_execution_time": avg_execution_time
            },
            "query_statistics": {
                "success_rates": query_success_rates,
                "data_availability_rates": data_availability_rates
            },
            "failure_analysis": {
                "failure_patterns": failure_patterns,
                "most_common_failures": sorted(
                    failure_patterns.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5]
            },
            "insights_and_recommendations": insights,
            "detailed_reports": [asdict(report) for report in user_reports[:10]]  # Include first 10 detailed reports
        }
        
        logger.info(
            f"Batch analysis complete: {successful_users}/{total_users} users successful "
            f"({(successful_users/total_users)*100:.1f}%), "
            f"execution time: {batch_execution_time:.2f}s"
        )
        
        return batch_results
    
    def _generate_batch_insights(
        self, 
        total_users: int, 
        successful_users: int, 
        failed_users: int,
        query_success_rates: Dict[str, float],
        data_availability_rates: Dict[str, float],
        failure_patterns: Dict[str, int]
    ) -> List[str]:
        """Generate insights and recommendations from batch analysis"""
        insights = []
        
        # Overall success rate insights
        success_rate = (successful_users / total_users) * 100
        if success_rate < 50:
            insights.append(f"CRITICAL: Only {success_rate:.1f}% of users have working preference queries")
        elif success_rate < 80:
            insights.append(f"WARNING: {success_rate:.1f}% success rate indicates systemic issues")
        else:
            insights.append(f"GOOD: {success_rate:.1f}% of users have functional preference queries")
        
        # Query-specific insights
        for query_name, success_rate in query_success_rates.items():
            data_rate = data_availability_rates[query_name]
            
            if success_rate < 50:
                insights.append(f"CRITICAL: {query_name} failing for {100-success_rate:.1f}% of users")
            elif data_rate < 30:
                insights.append(f"WARNING: {query_name} returns no data for {100-data_rate:.1f}% of users")
            elif data_rate > 80:
                insights.append(f"GOOD: {query_name} provides data for {data_rate:.1f}% of users")
        
        # Failure pattern insights
        if failure_patterns:
            most_common = max(failure_patterns.items(), key=lambda x: x[1])
            insights.append(f"Most common failure: {most_common[0]} ({most_common[1]} occurrences)")
            
            # Check for connection issues
            connection_failures = sum(count for pattern, count in failure_patterns.items() 
                                    if "Connection" in pattern or "Timeout" in pattern)
            if connection_failures > total_users * 0.1:
                insights.append("WARNING: High number of connection/timeout errors detected")
        
        # Recommendations
        if success_rate < 80:
            insights.append("RECOMMENDATION: Investigate database connectivity and query performance")
        
        if any(rate < 50 for rate in data_availability_rates.values()):
            insights.append("RECOMMENDATION: Review data migration and ETL processes for preference data")
        
        return insights
    
    def generate_comprehensive_report(self, anp_seq_list: List[int]) -> Dict[str, any]:
        """
        Generate a comprehensive diagnostic report for multiple users
        
        Args:
            anp_seq_list: List of user sequence numbers to analyze
            
        Returns:
            Comprehensive report with patterns and recommendations
        """
        logger.info(f"Generating comprehensive report for {len(anp_seq_list)} users")
        
        report_start_time = time.time()
        user_reports = []
        
        # Collect individual reports
        for anp_seq in anp_seq_list:
            try:
                report = self.diagnose_single_user(anp_seq)
                user_reports.append(report)
            except Exception as e:
                logger.error(f"Failed to generate report for anp_seq {anp_seq}: {e}")
        
        # Analyze patterns across all reports
        pattern_analysis = self._analyze_failure_patterns(user_reports)
        performance_analysis = self._analyze_performance_patterns(user_reports)
        data_quality_analysis = self._analyze_data_quality_patterns(user_reports)
        
        comprehensive_report = {
            "report_metadata": {
                "total_users_analyzed": len(user_reports),
                "generation_time": time.time() - report_start_time,
                "timestamp": datetime.now().isoformat()
            },
            "pattern_analysis": pattern_analysis,
            "performance_analysis": performance_analysis,
            "data_quality_analysis": data_quality_analysis,
            "individual_reports": [asdict(report) for report in user_reports]
        }
        
        logger.info(f"Comprehensive report generated in {time.time() - report_start_time:.2f}s")
        return comprehensive_report
    
    def _analyze_failure_patterns(self, reports: List[PreferenceDataReport]) -> Dict[str, any]:
        """Analyze failure patterns across multiple user reports"""
        failure_by_query = {}
        error_types = {}
        
        for report in reports:
            for diagnostic in report.diagnostics:
                query_name = diagnostic.query_name
                
                if query_name not in failure_by_query:
                    failure_by_query[query_name] = {"total": 0, "failures": 0, "empty_results": 0}
                
                failure_by_query[query_name]["total"] += 1
                
                if not diagnostic.success:
                    failure_by_query[query_name]["failures"] += 1
                    
                    if diagnostic.error_details:
                        error_type = diagnostic.error_details.split(':')[0]
                        error_types[error_type] = error_types.get(error_type, 0) + 1
                
                elif diagnostic.row_count == 0:
                    failure_by_query[query_name]["empty_results"] += 1
        
        return {
            "failure_rates_by_query": {
                query: {
                    "failure_rate": (stats["failures"] / stats["total"]) * 100,
                    "empty_result_rate": (stats["empty_results"] / stats["total"]) * 100,
                    "total_executions": stats["total"]
                }
                for query, stats in failure_by_query.items()
            },
            "common_error_types": sorted(error_types.items(), key=lambda x: x[1], reverse=True)
        }
    
    def _analyze_performance_patterns(self, reports: List[PreferenceDataReport]) -> Dict[str, any]:
        """Analyze performance patterns across multiple user reports"""
        execution_times_by_query = {}
        
        for report in reports:
            for diagnostic in report.diagnostics:
                query_name = diagnostic.query_name
                
                if query_name not in execution_times_by_query:
                    execution_times_by_query[query_name] = []
                
                execution_times_by_query[query_name].append(diagnostic.execution_time)
        
        performance_stats = {}
        for query_name, times in execution_times_by_query.items():
            if times:
                performance_stats[query_name] = {
                    "avg_execution_time": sum(times) / len(times),
                    "min_execution_time": min(times),
                    "max_execution_time": max(times),
                    "total_executions": len(times)
                }
        
        return performance_stats
    
    def _analyze_data_quality_patterns(self, reports: List[PreferenceDataReport]) -> Dict[str, any]:
        """Analyze data quality patterns across multiple user reports"""
        quality_scores_by_query = {}
        validation_issues = {}
        
        for report in reports:
            for diagnostic in report.diagnostics:
                query_name = diagnostic.query_name
                
                if query_name not in quality_scores_by_query:
                    quality_scores_by_query[query_name] = []
                
                if diagnostic.data_quality_score is not None:
                    quality_scores_by_query[query_name].append(diagnostic.data_quality_score)
                
                # Collect validation issues
                for issue in diagnostic.validation_issues:
                    validation_issues[issue] = validation_issues.get(issue, 0) + 1
        
        quality_stats = {}
        for query_name, scores in quality_scores_by_query.items():
            if scores:
                quality_stats[query_name] = {
                    "avg_quality_score": sum(scores) / len(scores),
                    "min_quality_score": min(scores),
                    "max_quality_score": max(scores),
                    "scores_below_threshold": len([s for s in scores if s < 0.5])
                }
        
        return {
            "quality_statistics": quality_stats,
            "common_validation_issues": sorted(
                validation_issues.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        }


class InteractivePreferenceDiagnostic:
    """
    Interactive command-line tool for preference data diagnostics
    """
    
    def __init__(self):
        self.analyzer = PreferenceDataAnalyzer()
        
    async def run_interactive_session(self):
        """Run interactive diagnostic session"""
        await self.analyzer.initialize()
        
        print("\n" + "="*60)
        print("  PREFERENCE DATA DIAGNOSTIC TOOL - INTERACTIVE MODE")
        print("="*60)
        print("\nAvailable commands:")
        print("  1. diagnose <anp_seq>     - Diagnose single user")
        print("  2. batch <start> <end>    - Batch analyze users")
        print("  3. report <anp_seq_list>  - Generate comprehensive report")
        print("  4. help                   - Show this help")
        print("  5. quit                   - Exit the tool")
        print("\nExamples:")
        print("  diagnose 12345")
        print("  batch 10000 10050")
        print("  report 12345,12346,12347")
        
        try:
            while True:
                try:
                    command = input("\npreference-diagnostic> ").strip()
                    
                    if not command:
                        continue
                    
                    parts = command.split()
                    cmd = parts[0].lower()
                    
                    if cmd == "quit" or cmd == "exit":
                        print("Goodbye!")
                        break
                    elif cmd == "help":
                        self._show_help()
                    elif cmd == "diagnose" and len(parts) == 2:
                        await self._handle_diagnose_command(parts[1])
                    elif cmd == "batch" and len(parts) == 3:
                        await self._handle_batch_command(parts[1], parts[2])
                    elif cmd == "report" and len(parts) == 2:
                        await self._handle_report_command(parts[1])
                    else:
                        print("Invalid command. Type 'help' for available commands.")
                        
                except KeyboardInterrupt:
                    print("\nUse 'quit' to exit.")
                except Exception as e:
                    print(f"Error: {e}")
                    
        finally:
            self.analyzer.cleanup()
    
    def _show_help(self):
        """Show detailed help information"""
        print("\nDETAILED COMMAND HELP:")
        print("\n1. diagnose <anp_seq>")
        print("   - Runs comprehensive diagnostics for a single user")
        print("   - Shows query execution results, timing, and data quality")
        print("   - Example: diagnose 12345")
        
        print("\n2. batch <start_anp_seq> <end_anp_seq>")
        print("   - Analyzes preference data for a range of users")
        print("   - Provides aggregate statistics and failure patterns")
        print("   - Example: batch 10000 10050")
        
        print("\n3. report <anp_seq_list>")
        print("   - Generates comprehensive report for specific users")
        print("   - Comma-separated list of anp_seq values")
        print("   - Example: report 12345,12346,12347")
        
        print("\n4. Output files:")
        print("   - Results can be saved to JSON files for further analysis")
        print("   - Use Ctrl+C to interrupt long-running operations")
    
    async def _handle_diagnose_command(self, anp_seq_str: str):
        """Handle single user diagnosis command"""
        try:
            anp_seq = int(anp_seq_str)
            print(f"\nDiagnosing preference data for user {anp_seq}...")
            
            report = self.analyzer.diagnose_single_user(anp_seq)
            self._print_diagnostic_report(report)
            
        except ValueError:
            print("Error: anp_seq must be a valid integer")
        except Exception as e:
            print(f"Error during diagnosis: {e}")
    
    async def _handle_batch_command(self, start_str: str, end_str: str):
        """Handle batch analysis command"""
        try:
            start_anp_seq = int(start_str)
            end_anp_seq = int(end_str)
            
            if start_anp_seq >= end_anp_seq:
                print("Error: start_anp_seq must be less than end_anp_seq")
                return
            
            total_users = end_anp_seq - start_anp_seq + 1
            if total_users > 100:
                confirm = input(f"This will analyze {total_users} users. Continue? (y/N): ")
                if confirm.lower() != 'y':
                    print("Batch analysis cancelled.")
                    return
            
            print(f"\nRunning batch analysis for {total_users} users...")
            
            results = self.analyzer.analyze_batch_users(start_anp_seq, end_anp_seq)
            self._print_batch_results(results)
            
        except ValueError:
            print("Error: start and end values must be valid integers")
        except Exception as e:
            print(f"Error during batch analysis: {e}")
    
    async def _handle_report_command(self, anp_seq_list_str: str):
        """Handle comprehensive report command"""
        try:
            anp_seq_list = [int(x.strip()) for x in anp_seq_list_str.split(',')]
            
            if len(anp_seq_list) > 50:
                confirm = input(f"This will analyze {len(anp_seq_list)} users. Continue? (y/N): ")
                if confirm.lower() != 'y':
                    print("Report generation cancelled.")
                    return
            
            print(f"\nGenerating comprehensive report for {len(anp_seq_list)} users...")
            
            report = self.analyzer.generate_comprehensive_report(anp_seq_list)
            self._print_comprehensive_report(report)
            
        except ValueError:
            print("Error: anp_seq_list must be comma-separated integers")
        except Exception as e:
            print(f"Error during report generation: {e}")
    
    def _print_diagnostic_report(self, report: PreferenceDataReport):
        """Print formatted diagnostic report for single user"""
        print(f"\n{'='*60}")
        print(f"DIAGNOSTIC REPORT for anp_seq: {report.anp_seq}")
        print(f"{'='*60}")
        
        print(f"\nSUMMARY:")
        print(f"  Total Queries: {report.total_queries}")
        print(f"  Successful: {report.successful_queries}")
        print(f"  Failed: {report.failed_queries}")
        print(f"  Success Rate: {(report.successful_queries/report.total_queries)*100:.1f}%")
        print(f"  Total Execution Time: {report.total_execution_time:.3f}s")
        
        print(f"\nQUERY DETAILS:")
        for diagnostic in report.diagnostics:
            status = "✓ SUCCESS" if diagnostic.success else "✗ FAILED"
            print(f"  {diagnostic.query_name}: {status}")
            print(f"    Execution Time: {diagnostic.execution_time:.3f}s")
            print(f"    Row Count: {diagnostic.row_count}")
            
            if diagnostic.data_quality_score is not None:
                print(f"    Data Quality: {diagnostic.data_quality_score:.2f}")
            
            if diagnostic.error_details:
                print(f"    Error: {diagnostic.error_details}")
            
            if diagnostic.validation_issues:
                print(f"    Issues: {', '.join(diagnostic.validation_issues)}")
            print()
        
        print(f"DATA AVAILABILITY:")
        for query_name, available in report.data_availability.items():
            status = "✓ Available" if available else "✗ No Data"
            print(f"  {query_name}: {status}")
        
        if report.recommendations:
            print(f"\nRECOMMENDATIONS:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"  {i}. {rec}")
    
    def _print_batch_results(self, results: Dict[str, any]):
        """Print formatted batch analysis results"""
        metadata = results["analysis_metadata"]
        summary = results["summary_statistics"]
        query_stats = results["query_statistics"]
        
        print(f"\n{'='*60}")
        print(f"BATCH ANALYSIS RESULTS")
        print(f"{'='*60}")
        
        print(f"\nANALYSIS SCOPE:")
        print(f"  Range: {metadata['start_anp_seq']} to {metadata['end_anp_seq']}")
        print(f"  Total Users: {metadata['total_users']}")
        print(f"  Analysis Time: {metadata['analysis_time']:.2f}s")
        
        print(f"\nOVERALL STATISTICS:")
        print(f"  Successful Users: {summary['successful_users']}")
        print(f"  Failed Users: {summary['failed_users']}")
        print(f"  Success Rate: {summary['success_rate']:.1f}%")
        print(f"  Avg Execution Time: {summary['avg_execution_time']:.3f}s")
        
        print(f"\nQUERY SUCCESS RATES:")
        for query_name, rate in query_stats["success_rates"].items():
            print(f"  {query_name}: {rate:.1f}%")
        
        print(f"\nDATA AVAILABILITY RATES:")
        for query_name, rate in query_stats["data_availability_rates"].items():
            print(f"  {query_name}: {rate:.1f}%")
        
        failure_analysis = results["failure_analysis"]
        if failure_analysis["most_common_failures"]:
            print(f"\nMOST COMMON FAILURES:")
            for pattern, count in failure_analysis["most_common_failures"]:
                print(f"  {pattern}: {count} occurrences")
        
        insights = results["insights_and_recommendations"]
        if insights:
            print(f"\nINSIGHTS & RECOMMENDATIONS:")
            for i, insight in enumerate(insights, 1):
                print(f"  {i}. {insight}")
    
    def _print_comprehensive_report(self, report: Dict[str, any]):
        """Print formatted comprehensive report"""
        metadata = report["report_metadata"]
        
        print(f"\n{'='*60}")
        print(f"COMPREHENSIVE DIAGNOSTIC REPORT")
        print(f"{'='*60}")
        
        print(f"\nREPORT METADATA:")
        print(f"  Users Analyzed: {metadata['total_users_analyzed']}")
        print(f"  Generation Time: {metadata['generation_time']:.2f}s")
        
        # Print pattern analysis
        pattern_analysis = report["pattern_analysis"]
        print(f"\nFAILURE PATTERN ANALYSIS:")
        for query_name, stats in pattern_analysis["failure_rates_by_query"].items():
            print(f"  {query_name}:")
            print(f"    Failure Rate: {stats['failure_rate']:.1f}%")
            print(f"    Empty Result Rate: {stats['empty_result_rate']:.1f}%")
            print(f"    Total Executions: {stats['total_executions']}")
        
        # Print performance analysis
        performance_analysis = report["performance_analysis"]
        print(f"\nPERFORMANCE ANALYSIS:")
        for query_name, stats in performance_analysis.items():
            print(f"  {query_name}:")
            print(f"    Avg Time: {stats['avg_execution_time']:.3f}s")
            print(f"    Min Time: {stats['min_execution_time']:.3f}s")
            print(f"    Max Time: {stats['max_execution_time']:.3f}s")
        
        # Print data quality analysis
        quality_analysis = report["data_quality_analysis"]
        if quality_analysis["quality_statistics"]:
            print(f"\nDATA QUALITY ANALYSIS:")
            for query_name, stats in quality_analysis["quality_statistics"].items():
                print(f"  {query_name}:")
                print(f"    Avg Quality Score: {stats['avg_quality_score']:.2f}")
                print(f"    Scores Below Threshold: {stats['scores_below_threshold']}")


def main():
    """Main entry point for the diagnostic tool"""
    parser = argparse.ArgumentParser(
        description="Preference Data Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python diagnose_preference_data.py --anp-seq 12345
  python diagnose_preference_data.py --batch-analyze --start 10000 --end 10100
  python diagnose_preference_data.py --interactive
  python diagnose_preference_data.py --report --anp-seq-list 12345,12346,12347 --output report.json
        """
    )
    
    parser.add_argument(
        "--anp-seq", 
        type=int, 
        help="Diagnose preference data for a single user"
    )
    
    parser.add_argument(
        "--batch-analyze", 
        action="store_true", 
        help="Run batch analysis across multiple users"
    )
    
    parser.add_argument(
        "--start", 
        type=int, 
        help="Starting anp_seq for batch analysis"
    )
    
    parser.add_argument(
        "--end", 
        type=int, 
        help="Ending anp_seq for batch analysis"
    )
    
    parser.add_argument(
        "--interactive", 
        action="store_true", 
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--report", 
        action="store_true", 
        help="Generate comprehensive report"
    )
    
    parser.add_argument(
        "--anp-seq-list", 
        type=str, 
        help="Comma-separated list of anp_seq values for report generation"
    )
    
    parser.add_argument(
        "--output", 
        type=str, 
        help="Output file path for JSON results"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if args.batch_analyze and (not args.start or not args.end):
        parser.error("--batch-analyze requires --start and --end arguments")
    
    if args.report and not args.anp_seq_list:
        parser.error("--report requires --anp-seq-list argument")
    
    async def run_diagnostic():
        analyzer = PreferenceDataAnalyzer()
        
        try:
            await analyzer.initialize()
            
            if args.interactive:
                interactive = InteractivePreferenceDiagnostic()
                await interactive.run_interactive_session()
                
            elif args.anp_seq:
                # Single user diagnosis
                report = analyzer.diagnose_single_user(args.anp_seq)
                
                print(f"\nDiagnostic Report for anp_seq: {args.anp_seq}")
                print("="*50)
                print(f"Success Rate: {(report.successful_queries/report.total_queries)*100:.1f}%")
                print(f"Execution Time: {report.total_execution_time:.3f}s")
                
                for diagnostic in report.diagnostics:
                    status = "SUCCESS" if diagnostic.success else "FAILED"
                    print(f"{diagnostic.query_name}: {status} ({diagnostic.execution_time:.3f}s, {diagnostic.row_count} rows)")
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(asdict(report), f, indent=2, default=str)
                    print(f"\nReport saved to: {args.output}")
                    
            elif args.batch_analyze:
                # Batch analysis
                results = analyzer.analyze_batch_users(args.start, args.end)
                
                print(f"\nBatch Analysis Results ({args.start} to {args.end})")
                print("="*50)
                summary = results["summary_statistics"]
                print(f"Success Rate: {summary['success_rate']:.1f}%")
                print(f"Successful Users: {summary['successful_users']}")
                print(f"Failed Users: {summary['failed_users']}")
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(results, f, indent=2, default=str)
                    print(f"\nResults saved to: {args.output}")
                    
            elif args.report:
                # Comprehensive report
                anp_seq_list = [int(x.strip()) for x in args.anp_seq_list.split(',')]
                report = analyzer.generate_comprehensive_report(anp_seq_list)
                
                print(f"\nComprehensive Report for {len(anp_seq_list)} users")
                print("="*50)
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(report, f, indent=2, default=str)
                    print(f"Report saved to: {args.output}")
                else:
                    print("Use --output to save detailed report to file")
                    
            else:
                parser.print_help()
                
        except Exception as e:
            logger.error(f"Diagnostic tool failed: {e}")
            sys.exit(1)
        finally:
            analyzer.cleanup()
    
    # Run the diagnostic tool
    asyncio.run(run_diagnostic())


if __name__ == "__main__":
    main()