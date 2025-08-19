#!/usr/bin/env python3
"""
Administrative Preference Data Management Tool

This tool provides comprehensive administrative capabilities for managing and
diagnosing preference data issues across the system. It includes interactive
commands, bulk operations, and reporting features.

Usage:
    python admin_preference_tool.py --help
    python admin_preference_tool.py health-check
    python admin_preference_tool.py bulk-diagnose --start 10000 --end 10100
    python admin_preference_tool.py pattern-analysis --sample-size 200
    python admin_preference_tool.py interactive
"""

import asyncio
import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import asdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import project modules
from database.connection import db_manager
from etl.preference_diagnostics import (
    PreferenceBulkAnalyzer,
    PreferencePatternDetector,
    AdminPreferenceDashboard,
    BulkAnalysisResult,
    PreferenceDataPattern,
    AdminDiagnosticSummary
)
from etl.legacy_query_executor import AptitudeTestQueries, PreferenceDataReport


class AdminPreferenceTool:
    """
    Main administrative tool for preference data management
    """
    
    def __init__(self):
        self.bulk_analyzer = None
        self.pattern_detector = None
        self.admin_dashboard = None
        self.session = None
        
    async def initialize(self):
        """Initialize all components"""
        try:
            self.session = db_manager.get_sync_session()
            
            self.bulk_analyzer = PreferenceBulkAnalyzer(max_workers=4)
            await self.bulk_analyzer.initialize()
            
            self.pattern_detector = PreferencePatternDetector()
            await self.pattern_detector.initialize()
            
            self.admin_dashboard = AdminPreferenceDashboard()
            await self.admin_dashboard.initialize()
            
            logger.info("Administrative tool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize administrative tool: {e}")
            raise
    
    def cleanup(self):
        """Clean up all resources"""
        if self.bulk_analyzer:
            self.bulk_analyzer.cleanup()
        if self.pattern_detector:
            self.pattern_detector.cleanup()
        if self.admin_dashboard:
            self.admin_dashboard.cleanup()
        if self.session:
            self.session.close()
        logger.info("Administrative tool cleaned up")
    
    async def health_check(self, sample_size: int = 50) -> AdminDiagnosticSummary:
        """
        Perform system health check
        
        Args:
            sample_size: Number of users to sample for health check
            
        Returns:
            AdminDiagnosticSummary with system health information
        """
        logger.info(f"Starting system health check with sample size {sample_size}")
        
        try:
            summary = await self.admin_dashboard.generate_health_summary(
                sample_size=sample_size
            )
            
            logger.info(
                f"Health check complete: Overall score {summary.overall_health_score:.1f}/100, "
                f"{len(summary.critical_issues)} critical issues, "
                f"{len(summary.warning_issues)} warnings"
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise
    
    async def bulk_diagnose(
        self, 
        start_anp_seq: int, 
        end_anp_seq: int,
        sample_size: Optional[int] = None,
        parallel: bool = True
    ) -> BulkAnalysisResult:
        """
        Perform bulk diagnosis across user range
        
        Args:
            start_anp_seq: Starting user sequence number
            end_anp_seq: Ending user sequence number
            sample_size: Optional sample size to limit analysis
            parallel: Whether to use parallel processing
            
        Returns:
            BulkAnalysisResult with comprehensive analysis
        """
        logger.info(f"Starting bulk diagnosis for range {start_anp_seq}-{end_anp_seq}")
        
        try:
            result = self.bulk_analyzer.analyze_user_range(
                start_anp_seq=start_anp_seq,
                end_anp_seq=end_anp_seq,
                sample_size=sample_size,
                parallel=parallel
            )
            
            logger.info(
                f"Bulk diagnosis complete: {result.successful_users}/{result.analyzed_users} "
                f"users successful in {result.analysis_duration:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Bulk diagnosis failed: {e}")
            raise
    
    async def pattern_analysis(
        self, 
        sample_size: int = 100,
        anp_seq_range: Optional[Tuple[int, int]] = None
    ) -> List[PreferenceDataPattern]:
        """
        Perform pattern analysis on preference data
        
        Args:
            sample_size: Number of users to analyze
            anp_seq_range: Optional range to sample from
            
        Returns:
            List of detected patterns
        """
        logger.info(f"Starting pattern analysis with sample size {sample_size}")
        
        try:
            # Determine sampling range
            if anp_seq_range:
                start_anp_seq, end_anp_seq = anp_seq_range
            else:
                start_anp_seq = 10000
                end_anp_seq = 20000
            
            # Collect reports for pattern analysis
            reports = []
            queries = AptitudeTestQueries(self.session)
            
            # Sample users from the range
            import random
            user_range = list(range(start_anp_seq, end_anp_seq + 1))
            sampled_users = random.sample(user_range, min(sample_size, len(user_range)))
            
            for anp_seq in sampled_users:
                try:
                    report = queries.diagnose_preference_queries(anp_seq)
                    reports.append(report)
                except Exception as e:
                    logger.warning(f"Failed to analyze anp_seq {anp_seq}: {e}")
            
            # Detect patterns
            patterns = self.pattern_detector.detect_patterns(reports)
            
            logger.info(f"Pattern analysis complete: {len(patterns)} patterns detected")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            raise
    
    async def diagnose_user(self, anp_seq: int) -> PreferenceDataReport:
        """
        Diagnose preference data for a specific user
        
        Args:
            anp_seq: User sequence number
            
        Returns:
            PreferenceDataReport with diagnostic information
        """
        logger.info(f"Diagnosing user {anp_seq}")
        
        try:
            queries = AptitudeTestQueries(self.session)
            report = queries.diagnose_preference_queries(anp_seq)
            
            logger.info(
                f"User diagnosis complete: {report.successful_queries}/{report.total_queries} "
                f"queries successful"
            )
            
            return report
            
        except Exception as e:
            logger.error(f"User diagnosis failed for anp_seq {anp_seq}: {e}")
            raise
    
    async def find_problematic_users(
        self, 
        start_anp_seq: int, 
        end_anp_seq: int,
        max_results: int = 50
    ) -> List[Tuple[int, PreferenceDataReport]]:
        """
        Find users with preference data problems
        
        Args:
            start_anp_seq: Starting user sequence number
            end_anp_seq: Ending user sequence number
            max_results: Maximum number of problematic users to return
            
        Returns:
            List of (anp_seq, report) tuples for problematic users
        """
        logger.info(f"Finding problematic users in range {start_anp_seq}-{end_anp_seq}")
        
        problematic_users = []
        queries = AptitudeTestQueries(self.session)
        
        try:
            for anp_seq in range(start_anp_seq, end_anp_seq + 1):
                if len(problematic_users) >= max_results:
                    break
                
                try:
                    report = queries.diagnose_preference_queries(anp_seq)
                    
                    # Check if user has problems
                    has_problems = (
                        report.failed_queries > 0 or
                        not all(report.data_availability.values()) or
                        any(d.data_quality_score and d.data_quality_score < 0.5 
                            for d in report.diagnostics if d.data_quality_score)
                    )
                    
                    if has_problems:
                        problematic_users.append((anp_seq, report))
                        
                except Exception as e:
                    logger.warning(f"Failed to check anp_seq {anp_seq}: {e}")
                    # Consider failed analysis as problematic
                    problematic_users.append((anp_seq, None))
            
            logger.info(f"Found {len(problematic_users)} problematic users")
            return problematic_users
            
        except Exception as e:
            logger.error(f"Failed to find problematic users: {e}")
            raise
    
    async def generate_report(
        self, 
        report_type: str,
        output_file: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Generate various types of reports
        
        Args:
            report_type: Type of report ('health', 'bulk', 'patterns', 'problems')
            output_file: Optional file to save report
            **kwargs: Additional arguments for specific report types
            
        Returns:
            Report data as dictionary
        """
        logger.info(f"Generating {report_type} report")
        
        try:
            if report_type == "health":
                sample_size = kwargs.get("sample_size", 100)
                summary = await self.health_check(sample_size)
                report_data = asdict(summary)
                
            elif report_type == "bulk":
                start_anp_seq = kwargs.get("start_anp_seq", 10000)
                end_anp_seq = kwargs.get("end_anp_seq", 10100)
                sample_size = kwargs.get("sample_size")
                
                result = await self.bulk_diagnose(start_anp_seq, end_anp_seq, sample_size)
                report_data = asdict(result)
                
            elif report_type == "patterns":
                sample_size = kwargs.get("sample_size", 100)
                anp_seq_range = kwargs.get("anp_seq_range")
                
                patterns = await self.pattern_analysis(sample_size, anp_seq_range)
                report_data = {
                    "patterns": [asdict(p) for p in patterns],
                    "summary": {
                        "total_patterns": len(patterns),
                        "critical_patterns": len([p for p in patterns if p.severity == "critical"]),
                        "high_patterns": len([p for p in patterns if p.severity == "high"]),
                        "medium_patterns": len([p for p in patterns if p.severity == "medium"]),
                        "low_patterns": len([p for p in patterns if p.severity == "low"])
                    }
                }
                
            elif report_type == "problems":
                start_anp_seq = kwargs.get("start_anp_seq", 10000)
                end_anp_seq = kwargs.get("end_anp_seq", 10100)
                max_results = kwargs.get("max_results", 50)
                
                problematic_users = await self.find_problematic_users(
                    start_anp_seq, end_anp_seq, max_results
                )
                
                report_data = {
                    "problematic_users": [
                        {
                            "anp_seq": anp_seq,
                            "report": asdict(report) if report else None
                        }
                        for anp_seq, report in problematic_users
                    ],
                    "summary": {
                        "total_problematic": len(problematic_users),
                        "analysis_range": f"{start_anp_seq}-{end_anp_seq}"
                    }
                }
                
            else:
                raise ValueError(f"Unknown report type: {report_type}")
            
            # Add metadata
            report_data["metadata"] = {
                "report_type": report_type,
                "generated_at": datetime.now().isoformat(),
                "generated_by": "admin_preference_tool"
            }
            
            # Save to file if requested
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(report_data, f, indent=2, default=str)
                logger.info(f"Report saved to {output_file}")
            
            return report_data
            
        except Exception as e:
            logger.error(f"Failed to generate {report_type} report: {e}")
            raise


class InteractiveAdminTool:
    """
    Interactive command-line interface for administrative operations
    """
    
    def __init__(self):
        self.admin_tool = AdminPreferenceTool()
        
    async def run_interactive_session(self):
        """Run interactive administrative session"""
        await self.admin_tool.initialize()
        
        print("\n" + "="*70)
        print("  PREFERENCE DATA ADMINISTRATIVE TOOL - INTERACTIVE MODE")
        print("="*70)
        print("\nAvailable commands:")
        print("  health                    - System health check")
        print("  bulk <start> <end>        - Bulk diagnosis")
        print("  patterns [sample_size]    - Pattern analysis")
        print("  diagnose <anp_seq>        - Diagnose specific user")
        print("  problems <start> <end>    - Find problematic users")
        print("  report <type> [options]   - Generate report")
        print("  status                    - Show system status")
        print("  help                      - Show detailed help")
        print("  quit                      - Exit the tool")
        
        try:
            while True:
                try:
                    command = input("\nadmin-preference> ").strip()
                    
                    if not command:
                        continue
                    
                    parts = command.split()
                    cmd = parts[0].lower()
                    
                    if cmd in ["quit", "exit"]:
                        print("Goodbye!")
                        break
                    elif cmd == "help":
                        self._show_detailed_help()
                    elif cmd == "health":
                        await self._handle_health_command()
                    elif cmd == "bulk" and len(parts) >= 3:
                        await self._handle_bulk_command(parts[1], parts[2])
                    elif cmd == "patterns":
                        sample_size = int(parts[1]) if len(parts) > 1 else 100
                        await self._handle_patterns_command(sample_size)
                    elif cmd == "diagnose" and len(parts) == 2:
                        await self._handle_diagnose_command(parts[1])
                    elif cmd == "problems" and len(parts) >= 3:
                        await self._handle_problems_command(parts[1], parts[2])
                    elif cmd == "report" and len(parts) >= 2:
                        await self._handle_report_command(parts[1:])
                    elif cmd == "status":
                        await self._handle_status_command()
                    else:
                        print("Invalid command. Type 'help' for available commands.")
                        
                except KeyboardInterrupt:
                    print("\nUse 'quit' to exit.")
                except Exception as e:
                    print(f"Error: {e}")
                    
        finally:
            self.admin_tool.cleanup()
    
    def _show_detailed_help(self):
        """Show detailed help information"""
        print("\nDETAILED COMMAND HELP:")
        
        print("\n1. health")
        print("   - Performs comprehensive system health check")
        print("   - Samples users and analyzes overall system status")
        print("   - Shows health score, critical issues, and recommendations")
        
        print("\n2. bulk <start_anp_seq> <end_anp_seq>")
        print("   - Runs bulk diagnosis across user range")
        print("   - Provides aggregate statistics and failure patterns")
        print("   - Example: bulk 10000 10100")
        
        print("\n3. patterns [sample_size]")
        print("   - Analyzes patterns in preference data")
        print("   - Detects systematic issues and trends")
        print("   - Default sample size: 100")
        print("   - Example: patterns 200")
        
        print("\n4. diagnose <anp_seq>")
        print("   - Diagnoses preference data for specific user")
        print("   - Shows detailed query results and issues")
        print("   - Example: diagnose 12345")
        
        print("\n5. problems <start_anp_seq> <end_anp_seq>")
        print("   - Finds users with preference data problems")
        print("   - Lists users with failures or data quality issues")
        print("   - Example: problems 10000 10100")
        
        print("\n6. report <type> [options]")
        print("   - Generates various types of reports")
        print("   - Types: health, bulk, patterns, problems")
        print("   - Example: report health")
        
        print("\n7. status")
        print("   - Shows current system status and recent activity")
    
    async def _handle_health_command(self):
        """Handle health check command"""
        print("\nPerforming system health check...")
        
        try:
            summary = await self.admin_tool.health_check()
            
            print(f"\n{'='*50}")
            print(f"SYSTEM HEALTH REPORT")
            print(f"{'='*50}")
            
            print(f"\nOverall Health Score: {summary.overall_health_score:.1f}/100")
            
            if summary.overall_health_score >= 80:
                print("Status: HEALTHY ✓")
            elif summary.overall_health_score >= 60:
                print("Status: WARNING ⚠")
            else:
                print("Status: CRITICAL ✗")
            
            print(f"\nUsers Checked: {summary.total_users_checked}")
            print(f"Critical Issues: {len(summary.critical_issues)}")
            print(f"Warning Issues: {len(summary.warning_issues)}")
            
            if summary.critical_issues:
                print(f"\nCRITICAL ISSUES:")
                for issue in summary.critical_issues[:3]:  # Show top 3
                    print(f"  • {issue.pattern_name}")
                    print(f"    Affected: {len(issue.affected_users)} users")
            
            if summary.system_recommendations:
                print(f"\nRECOMMENDATIONS:")
                for i, rec in enumerate(summary.system_recommendations[:3], 1):
                    print(f"  {i}. {rec}")
            
        except Exception as e:
            print(f"Health check failed: {e}")
    
    async def _handle_bulk_command(self, start_str: str, end_str: str):
        """Handle bulk diagnosis command"""
        try:
            start_anp_seq = int(start_str)
            end_anp_seq = int(end_str)
            
            total_users = end_anp_seq - start_anp_seq + 1
            if total_users > 500:
                confirm = input(f"This will analyze {total_users} users. Continue? (y/N): ")
                if confirm.lower() != 'y':
                    print("Bulk analysis cancelled.")
                    return
            
            print(f"\nRunning bulk diagnosis for {total_users} users...")
            
            result = await self.admin_tool.bulk_diagnose(start_anp_seq, end_anp_seq)
            
            print(f"\n{'='*50}")
            print(f"BULK DIAGNOSIS RESULTS")
            print(f"{'='*50}")
            
            print(f"\nRange: {result.start_anp_seq} to {result.end_anp_seq}")
            print(f"Total Users: {result.total_users}")
            print(f"Analyzed: {result.analyzed_users}")
            print(f"Successful: {result.successful_users}")
            print(f"Failed: {result.failed_users}")
            print(f"Success Rate: {(result.successful_users/result.analyzed_users)*100:.1f}%")
            print(f"Analysis Time: {result.analysis_duration:.2f}s")
            
            print(f"\nQUERY SUCCESS RATES:")
            for query_name, rate in result.query_success_rates.items():
                print(f"  {query_name}: {rate:.1f}%")
            
            if result.failure_patterns:
                print(f"\nTOP FAILURE PATTERNS:")
                sorted_patterns = sorted(
                    result.failure_patterns.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
                for pattern, count in sorted_patterns[:3]:
                    print(f"  {pattern}: {count} occurrences")
            
        except ValueError:
            print("Error: start and end values must be valid integers")
        except Exception as e:
            print(f"Bulk diagnosis failed: {e}")
    
    async def _handle_patterns_command(self, sample_size: int):
        """Handle pattern analysis command"""
        print(f"\nAnalyzing patterns with sample size {sample_size}...")
        
        try:
            patterns = await self.admin_tool.pattern_analysis(sample_size)
            
            print(f"\n{'='*50}")
            print(f"PATTERN ANALYSIS RESULTS")
            print(f"{'='*50}")
            
            print(f"\nTotal Patterns Detected: {len(patterns)}")
            
            # Group by severity
            by_severity = {}
            for pattern in patterns:
                by_severity.setdefault(pattern.severity, []).append(pattern)
            
            for severity in ["critical", "high", "medium", "low"]:
                if severity in by_severity:
                    print(f"{severity.upper()}: {len(by_severity[severity])}")
            
            # Show top patterns
            if patterns:
                print(f"\nTOP PATTERNS:")
                for i, pattern in enumerate(patterns[:5], 1):
                    print(f"  {i}. {pattern.pattern_name} ({pattern.severity})")
                    print(f"     Affected Users: {len(pattern.affected_users)}")
                    print(f"     Confidence: {pattern.confidence_score:.2f}")
            
        except Exception as e:
            print(f"Pattern analysis failed: {e}")
    
    async def _handle_diagnose_command(self, anp_seq_str: str):
        """Handle single user diagnosis command"""
        try:
            anp_seq = int(anp_seq_str)
            print(f"\nDiagnosing user {anp_seq}...")
            
            report = await self.admin_tool.diagnose_user(anp_seq)
            
            print(f"\n{'='*50}")
            print(f"USER DIAGNOSIS: {anp_seq}")
            print(f"{'='*50}")
            
            print(f"\nSummary:")
            print(f"  Success Rate: {(report.successful_queries/report.total_queries)*100:.1f}%")
            print(f"  Execution Time: {report.total_execution_time:.3f}s")
            
            print(f"\nQuery Results:")
            for diagnostic in report.diagnostics:
                status = "✓" if diagnostic.success else "✗"
                print(f"  {status} {diagnostic.query_name}")
                print(f"    Time: {diagnostic.execution_time:.3f}s")
                print(f"    Rows: {diagnostic.row_count}")
                
                if diagnostic.error_details:
                    print(f"    Error: {diagnostic.error_details}")
                
                if diagnostic.validation_issues:
                    print(f"    Issues: {', '.join(diagnostic.validation_issues)}")
            
        except ValueError:
            print("Error: anp_seq must be a valid integer")
        except Exception as e:
            print(f"User diagnosis failed: {e}")
    
    async def _handle_problems_command(self, start_str: str, end_str: str):
        """Handle find problems command"""
        try:
            start_anp_seq = int(start_str)
            end_anp_seq = int(end_str)
            
            print(f"\nFinding problematic users in range {start_anp_seq}-{end_anp_seq}...")
            
            problematic_users = await self.admin_tool.find_problematic_users(
                start_anp_seq, end_anp_seq
            )
            
            print(f"\n{'='*50}")
            print(f"PROBLEMATIC USERS")
            print(f"{'='*50}")
            
            print(f"\nFound {len(problematic_users)} problematic users:")
            
            for anp_seq, report in problematic_users[:10]:  # Show first 10
                if report:
                    failed_queries = report.failed_queries
                    missing_data = sum(1 for available in report.data_availability.values() if not available)
                    print(f"  {anp_seq}: {failed_queries} failures, {missing_data} missing data")
                else:
                    print(f"  {anp_seq}: Analysis failed")
            
            if len(problematic_users) > 10:
                print(f"  ... and {len(problematic_users) - 10} more")
            
        except ValueError:
            print("Error: start and end values must be valid integers")
        except Exception as e:
            print(f"Find problems failed: {e}")
    
    async def _handle_report_command(self, args: List[str]):
        """Handle report generation command"""
        if not args:
            print("Error: report type required (health, bulk, patterns, problems)")
            return
        
        report_type = args[0]
        
        print(f"\nGenerating {report_type} report...")
        
        try:
            # Generate timestamp-based filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"preference_{report_type}_report_{timestamp}.json"
            
            report_data = await self.admin_tool.generate_report(
                report_type=report_type,
                output_file=output_file
            )
            
            print(f"Report generated successfully!")
            print(f"Saved to: {output_file}")
            
            # Show brief summary
            if "summary" in report_data:
                print(f"\nSummary:")
                for key, value in report_data["summary"].items():
                    print(f"  {key}: {value}")
            
        except Exception as e:
            print(f"Report generation failed: {e}")
    
    async def _handle_status_command(self):
        """Handle status command"""
        print(f"\n{'='*50}")
        print(f"SYSTEM STATUS")
        print(f"{'='*50}")
        
        print(f"\nCurrent Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Tool Status: Active")
        print(f"Database Connection: Connected")
        
        # Quick health check
        try:
            summary = await self.admin_tool.health_check(sample_size=10)
            print(f"Quick Health Score: {summary.overall_health_score:.1f}/100")
            
            if summary.critical_issues:
                print(f"Critical Issues: {len(summary.critical_issues)}")
            else:
                print("Critical Issues: None")
                
        except Exception as e:
            print(f"Health Check: Failed ({e})")


def main():
    """Main entry point for the administrative tool"""
    parser = argparse.ArgumentParser(
        description="Administrative Preference Data Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python admin_preference_tool.py health-check
  python admin_preference_tool.py bulk-diagnose --start 10000 --end 10100
  python admin_preference_tool.py pattern-analysis --sample-size 200
  python admin_preference_tool.py find-problems --start 10000 --end 10050
  python admin_preference_tool.py generate-report health --output health_report.json
  python admin_preference_tool.py interactive
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Health check command
    health_parser = subparsers.add_parser('health-check', help='Perform system health check')
    health_parser.add_argument('--sample-size', type=int, default=50, help='Sample size for health check')
    health_parser.add_argument('--output', type=str, help='Output file for health report')
    
    # Bulk diagnose command
    bulk_parser = subparsers.add_parser('bulk-diagnose', help='Perform bulk diagnosis')
    bulk_parser.add_argument('--start', type=int, required=True, help='Starting anp_seq')
    bulk_parser.add_argument('--end', type=int, required=True, help='Ending anp_seq')
    bulk_parser.add_argument('--sample-size', type=int, help='Sample size to limit analysis')
    bulk_parser.add_argument('--output', type=str, help='Output file for results')
    
    # Pattern analysis command
    pattern_parser = subparsers.add_parser('pattern-analysis', help='Analyze patterns in preference data')
    pattern_parser.add_argument('--sample-size', type=int, default=100, help='Sample size for analysis')
    pattern_parser.add_argument('--start', type=int, help='Starting anp_seq for sampling')
    pattern_parser.add_argument('--end', type=int, help='Ending anp_seq for sampling')
    pattern_parser.add_argument('--output', type=str, help='Output file for patterns')
    
    # Find problems command
    problems_parser = subparsers.add_parser('find-problems', help='Find users with preference data problems')
    problems_parser.add_argument('--start', type=int, required=True, help='Starting anp_seq')
    problems_parser.add_argument('--end', type=int, required=True, help='Ending anp_seq')
    problems_parser.add_argument('--max-results', type=int, default=50, help='Maximum problematic users to find')
    problems_parser.add_argument('--output', type=str, help='Output file for results')
    
    # Generate report command
    report_parser = subparsers.add_parser('generate-report', help='Generate various types of reports')
    report_parser.add_argument('type', choices=['health', 'bulk', 'patterns', 'problems'], help='Report type')
    report_parser.add_argument('--output', type=str, help='Output file for report')
    report_parser.add_argument('--sample-size', type=int, default=100, help='Sample size')
    report_parser.add_argument('--start', type=int, help='Starting anp_seq')
    report_parser.add_argument('--end', type=int, help='Ending anp_seq')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Run in interactive mode')
    
    # Diagnose user command
    diagnose_parser = subparsers.add_parser('diagnose-user', help='Diagnose specific user')
    diagnose_parser.add_argument('anp_seq', type=int, help='User sequence number to diagnose')
    diagnose_parser.add_argument('--output', type=str, help='Output file for diagnosis')
    
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    async def run_command():
        if args.command == 'interactive':
            interactive_tool = InteractiveAdminTool()
            await interactive_tool.run_interactive_session()
            return
        
        # For non-interactive commands, initialize the tool
        admin_tool = AdminPreferenceTool()
        
        try:
            await admin_tool.initialize()
            
            if args.command == 'health-check':
                summary = await admin_tool.health_check(args.sample_size)
                
                print(f"\nSystem Health Score: {summary.overall_health_score:.1f}/100")
                print(f"Critical Issues: {len(summary.critical_issues)}")
                print(f"Warning Issues: {len(summary.warning_issues)}")
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(asdict(summary), f, indent=2, default=str)
                    print(f"Health report saved to: {args.output}")
                    
            elif args.command == 'bulk-diagnose':
                result = await admin_tool.bulk_diagnose(
                    args.start, args.end, args.sample_size
                )
                
                print(f"\nBulk Analysis Results:")
                print(f"Success Rate: {(result.successful_users/result.analyzed_users)*100:.1f}%")
                print(f"Analysis Time: {result.analysis_duration:.2f}s")
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(asdict(result), f, indent=2, default=str)
                    print(f"Results saved to: {args.output}")
                    
            elif args.command == 'pattern-analysis':
                anp_seq_range = (args.start, args.end) if args.start and args.end else None
                patterns = await admin_tool.pattern_analysis(args.sample_size, anp_seq_range)
                
                print(f"\nPattern Analysis Results:")
                print(f"Total Patterns: {len(patterns)}")
                
                by_severity = {}
                for pattern in patterns:
                    by_severity.setdefault(pattern.severity, []).append(pattern)
                
                for severity in ["critical", "high", "medium", "low"]:
                    if severity in by_severity:
                        print(f"{severity.upper()}: {len(by_severity[severity])}")
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump([asdict(p) for p in patterns], f, indent=2, default=str)
                    print(f"Patterns saved to: {args.output}")
                    
            elif args.command == 'find-problems':
                problematic_users = await admin_tool.find_problematic_users(
                    args.start, args.end, args.max_results
                )
                
                print(f"\nFound {len(problematic_users)} problematic users")
                
                if args.output:
                    data = [
                        {"anp_seq": anp_seq, "report": asdict(report) if report else None}
                        for anp_seq, report in problematic_users
                    ]
                    with open(args.output, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
                    print(f"Results saved to: {args.output}")
                    
            elif args.command == 'generate-report':
                kwargs = {}
                if args.sample_size:
                    kwargs['sample_size'] = args.sample_size
                if args.start:
                    kwargs['start_anp_seq'] = args.start
                if args.end:
                    kwargs['end_anp_seq'] = args.end
                
                report_data = await admin_tool.generate_report(
                    args.type, args.output, **kwargs
                )
                
                print(f"\n{args.type.title()} report generated successfully")
                if args.output:
                    print(f"Saved to: {args.output}")
                    
            elif args.command == 'diagnose-user':
                report = await admin_tool.diagnose_user(args.anp_seq)
                
                print(f"\nUser {args.anp_seq} Diagnosis:")
                print(f"Success Rate: {(report.successful_queries/report.total_queries)*100:.1f}%")
                print(f"Execution Time: {report.total_execution_time:.3f}s")
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(asdict(report), f, indent=2, default=str)
                    print(f"Diagnosis saved to: {args.output}")
                    
            else:
                parser.print_help()
                
        except Exception as e:
            logger.error(f"Command failed: {e}")
            sys.exit(1)
        finally:
            admin_tool.cleanup()
    
    # Run the command
    if not args.command:
        parser.print_help()
    else:
        asyncio.run(run_command())


if __name__ == "__main__":
    main()