#!/usr/bin/env python3
"""
Command-line administrative tool for preference data management.

This tool provides interactive commands for diagnosing, testing, and repairing
preference data issues across the system.
"""

import asyncio
import argparse
import sys
import json
from typing import Optional, List
import logging
from datetime import datetime

from etl.preference_diagnostics import PreferenceDiagnostics
from etl.preference_data_validator import PreferenceDataValidator
from etl.legacy_query_executor import LegacyQueryExecutor
from database.connection import db_manager
from database.repositories import DocumentRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PreferenceAdminCLI:
    """Command-line interface for preference data administration"""
    
    def __init__(self):
        self.diagnostics = PreferenceDiagnostics()
        self.validator = PreferenceDataValidator()
        
    async def initialize(self):
        """Initialize the CLI tool"""
        await self.diagnostics.initialize()
        
    def cleanup(self):
        """Clean up resources"""
        self.diagnostics.cleanup()

    async def diagnose_user(self, anp_seq: int, verbose: bool = False) -> None:
        """Diagnose preference data for a specific user"""
        print(f"\n🔍 Diagnosing preference data for user {anp_seq}...")
        
        try:
            result = await self.diagnostics.diagnose_user_preference_data(anp_seq)
            
            print(f"\n📊 Diagnostic Results for User {anp_seq}")
            print("=" * 50)
            
            # Query status
            print("\n📋 Query Status:")
            for query_name, status in result["query_status"].items():
                success_icon = "✅" if status.get("success", False) else "❌"
                print(f"  {success_icon} {query_name}")
                
                if verbose:
                    if status.get("success", False):
                        row_count = status.get("row_count", 0)
                        has_data = status.get("has_data", False)
                        data_icon = "📊" if has_data else "📭"
                        print(f"      {data_icon} Rows: {row_count}, Has Data: {has_data}")
                    else:
                        error = status.get("error", "Unknown error")
                        print(f"      ❗ Error: {error}")
            
            # Issues
            if result["issues"]:
                print(f"\n⚠️  Issues Found ({len(result['issues'])}):")
                for i, issue in enumerate(result["issues"], 1):
                    print(f"  {i}. {issue}")
            else:
                print("\n✅ No issues found!")
            
            # Recommendations
            if result["recommendations"]:
                print(f"\n💡 Recommendations:")
                for i, rec in enumerate(result["recommendations"], 1):
                    print(f"  {i}. {rec}")
            
            # Validation results (if verbose)
            if verbose and result["validation_results"]:
                print(f"\n🔍 Validation Details:")
                for data_type, validation in result["validation_results"].items():
                    is_valid = validation.get("is_valid", False)
                    valid_icon = "✅" if is_valid else "❌"
                    print(f"  {valid_icon} {data_type}")
                    
                    if not is_valid and "issues" in validation:
                        for issue in validation["issues"]:
                            print(f"      ❗ {issue}")
            
        except Exception as e:
            print(f"❌ Error during diagnosis: {str(e)}")
            logger.error(f"Diagnosis failed for anp_seq {anp_seq}: {str(e)}")

    async def test_queries(self, anp_seq: int, include_sample: bool = False) -> None:
        """Test all preference queries for a specific user"""
        print(f"\n🧪 Testing preference queries for user {anp_seq}...")
        
        try:
            query_executor = LegacyQueryExecutor()
            
            # Test each query
            queries = [
                ("Image Preference Stats", query_executor.imagePreferenceStatsQuery),
                ("Preference Data", query_executor.preferenceDataQuery),
                ("Preference Jobs", query_executor.preferenceJobsQuery)
            ]
            
            print(f"\n📋 Query Test Results")
            print("=" * 50)
            
            for query_name, query_method in queries:
                start_time = datetime.now()
                
                try:
                    result = await query_method(anp_seq)
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000
                    row_count = len(result) if result else 0
                    
                    print(f"\n✅ {query_name}")
                    print(f"   ⏱️  Execution Time: {execution_time:.2f}ms")
                    print(f"   📊 Row Count: {row_count}")
                    print(f"   📭 Has Data: {'Yes' if result else 'No'}")
                    
                    if include_sample and result:
                        print(f"   📄 Sample Data (first 2 rows):")
                        for i, row in enumerate(result[:2]):
                            print(f"      {i+1}. {dict(row)}")
                    
                except Exception as e:
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000
                    print(f"\n❌ {query_name}")
                    print(f"   ⏱️  Execution Time: {execution_time:.2f}ms")
                    print(f"   ❗ Error: {str(e)}")
            
        except Exception as e:
            print(f"❌ Error during query testing: {str(e)}")
            logger.error(f"Query testing failed for anp_seq {anp_seq}: {str(e)}")

    async def repair_user(self, anp_seq: int, force: bool = False) -> None:
        """Repair preference data for a specific user"""
        print(f"\n🔧 Repairing preference data for user {anp_seq}...")
        
        if not force:
            # First run diagnosis to see if repair is needed
            diagnostic_result = await self.diagnostics.diagnose_user_preference_data(anp_seq)
            
            if not diagnostic_result["issues"]:
                print("✅ No issues found. Repair not needed.")
                print("   Use --force to repair anyway.")
                return
            
            print(f"⚠️  Found {len(diagnostic_result['issues'])} issues. Proceeding with repair...")
        
        try:
            repair_result = await self.diagnostics.repair_user_preference_data(anp_seq)
            
            print(f"\n🔧 Repair Results for User {anp_seq}")
            print("=" * 50)
            
            # Show steps completed
            if repair_result["steps_completed"]:
                print("\n📋 Steps Completed:")
                for i, step in enumerate(repair_result["steps_completed"], 1):
                    print(f"  {i}. {step}")
            
            # Show final result
            if repair_result["success"]:
                docs_created = repair_result["documents_created"]
                print(f"\n✅ Repair Successful!")
                print(f"   📄 Documents Created: {docs_created}")
            else:
                error = repair_result.get("error", "Unknown error")
                print(f"\n❌ Repair Failed!")
                print(f"   ❗ Error: {error}")
            
        except Exception as e:
            print(f"❌ Error during repair: {str(e)}")
            logger.error(f"Repair failed for anp_seq {anp_seq}: {str(e)}")

    async def bulk_diagnose(self, start_anp_seq: int, end_anp_seq: int, 
                           only_issues: bool = False, limit: int = 100) -> None:
        """Run bulk diagnosis on a range of users"""
        print(f"\n🔍 Running bulk diagnosis for users {start_anp_seq}-{end_anp_seq}...")
        
        try:
            async with db_manager.get_async_session() as db_session:
                doc_repo = DocumentRepository(db_session)
                
                # Get users in range
                all_users = await doc_repo.get_unique_anp_seqs(limit=end_anp_seq - start_anp_seq + 1)
                users_in_range = [u for u in all_users if start_anp_seq <= u <= end_anp_seq]
                
                if len(users_in_range) > limit:
                    users_in_range = users_in_range[:limit]
                    print(f"⚠️  Limited to first {limit} users")
                
                print(f"📊 Analyzing {len(users_in_range)} users...")
                
                users_with_issues = 0
                users_without_preference_data = 0
                common_issues = {}
                
                for i, anp_seq in enumerate(users_in_range):
                    if (i + 1) % 10 == 0:
                        progress = ((i + 1) / len(users_in_range)) * 100
                        print(f"   Progress: {progress:.1f}% ({i + 1}/{len(users_in_range)})")
                    
                    try:
                        # Run diagnostic
                        diagnostic_result = await self.diagnostics.diagnose_user_preference_data(anp_seq)
                        
                        # Check for preference documents
                        documents = await doc_repo.get_documents_by_anp_seq(anp_seq)
                        preference_docs = [doc for doc in documents if doc.document_type == "PREFERENCE_ANALYSIS"]
                        
                        has_issues = len(diagnostic_result.get("issues", [])) > 0
                        has_preference_data = len(preference_docs) > 0
                        
                        if not has_preference_data:
                            users_without_preference_data += 1
                        
                        if has_issues:
                            users_with_issues += 1
                            
                            # Count common issues
                            for issue in diagnostic_result.get("issues", []):
                                common_issues[issue] = common_issues.get(issue, 0) + 1
                        
                        # Show individual results if requested or has issues
                        if not only_issues or has_issues or not has_preference_data:
                            status_icon = "❌" if has_issues else ("⚠️" if not has_preference_data else "✅")
                            print(f"   {status_icon} User {anp_seq}: {len(diagnostic_result.get('issues', []))} issues, "
                                  f"{len(preference_docs)} preference docs")
                    
                    except Exception as e:
                        print(f"   ❌ User {anp_seq}: Analysis failed - {str(e)}")
                        continue
                
                # Summary
                print(f"\n📊 Bulk Diagnosis Summary")
                print("=" * 50)
                print(f"Total Users Analyzed: {len(users_in_range)}")
                print(f"Users with Issues: {users_with_issues}")
                print(f"Users without Preference Data: {users_without_preference_data}")
                
                if common_issues:
                    print(f"\n🔍 Most Common Issues:")
                    sorted_issues = sorted(common_issues.items(), key=lambda x: x[1], reverse=True)
                    for issue, count in sorted_issues[:5]:
                        print(f"   {count:3d}x {issue}")
                
        except Exception as e:
            print(f"❌ Error during bulk diagnosis: {str(e)}")
            logger.error(f"Bulk diagnosis failed: {str(e)}")

    async def system_overview(self) -> None:
        """Show system-wide preference data overview"""
        print(f"\n📊 System Preference Data Overview")
        print("=" * 50)
        
        try:
            async with db_manager.get_async_session() as db_session:
                doc_repo = DocumentRepository(db_session)
                
                # Get basic statistics
                total_users = await doc_repo.get_total_user_count()
                users_with_preference_docs = await doc_repo.get_users_with_document_type("PREFERENCE_ANALYSIS")
                
                # Calculate percentages
                preference_coverage = (len(users_with_preference_docs) / total_users * 100) if total_users > 0 else 0
                
                print(f"Total Users: {total_users}")
                print(f"Users with Preference Documents: {len(users_with_preference_docs)}")
                print(f"Preference Data Coverage: {preference_coverage:.1f}%")
                print(f"Users Missing Preference Data: {total_users - len(users_with_preference_docs)}")
                
                # Health assessment
                if preference_coverage >= 90:
                    health_status = "🟢 Excellent"
                elif preference_coverage >= 70:
                    health_status = "🟡 Good"
                elif preference_coverage >= 50:
                    health_status = "🟠 Fair"
                else:
                    health_status = "🔴 Poor"
                
                print(f"\nSystem Health: {health_status}")
                
        except Exception as e:
            print(f"❌ Error getting system overview: {str(e)}")
            logger.error(f"System overview failed: {str(e)}")


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Administrative tool for preference data management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Diagnose a specific user
  python admin_preference_cli.py diagnose 12345

  # Test queries for a user with sample data
  python admin_preference_cli.py test 12345 --include-sample

  # Repair a user's preference data
  python admin_preference_cli.py repair 12345

  # Bulk diagnose users in a range
  python admin_preference_cli.py bulk-diagnose 10000 15000 --only-issues

  # Show system overview
  python admin_preference_cli.py overview
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Diagnose command
    diagnose_parser = subparsers.add_parser('diagnose', help='Diagnose preference data for a user')
    diagnose_parser.add_argument('anp_seq', type=int, help='User sequence number')
    diagnose_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed information')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test preference queries for a user')
    test_parser.add_argument('anp_seq', type=int, help='User sequence number')
    test_parser.add_argument('--include-sample', action='store_true', help='Include sample data in output')
    
    # Repair command
    repair_parser = subparsers.add_parser('repair', help='Repair preference data for a user')
    repair_parser.add_argument('anp_seq', type=int, help='User sequence number')
    repair_parser.add_argument('--force', action='store_true', help='Force repair even if no issues detected')
    
    # Bulk diagnose command
    bulk_parser = subparsers.add_parser('bulk-diagnose', help='Run bulk diagnosis on user range')
    bulk_parser.add_argument('start_anp_seq', type=int, help='Starting user sequence number')
    bulk_parser.add_argument('end_anp_seq', type=int, help='Ending user sequence number')
    bulk_parser.add_argument('--only-issues', action='store_true', help='Only show users with issues')
    bulk_parser.add_argument('--limit', type=int, default=100, help='Maximum users to check')
    
    # Overview command
    subparsers.add_parser('overview', help='Show system-wide preference data overview')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI tool
    cli = PreferenceAdminCLI()
    
    try:
        await cli.initialize()
        
        # Execute command
        if args.command == 'diagnose':
            await cli.diagnose_user(args.anp_seq, args.verbose)
        elif args.command == 'test':
            await cli.test_queries(args.anp_seq, args.include_sample)
        elif args.command == 'repair':
            await cli.repair_user(args.anp_seq, args.force)
        elif args.command == 'bulk-diagnose':
            await cli.bulk_diagnose(args.start_anp_seq, args.end_anp_seq, args.only_issues, args.limit)
        elif args.command == 'overview':
            await cli.system_overview()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        logger.error(f"CLI error: {str(e)}")
    finally:
        cli.cleanup()


if __name__ == "__main__":
    asyncio.run(main())