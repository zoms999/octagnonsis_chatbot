"""
Comprehensive test runner for preference data processing validation
Executes all preference-related tests and provides detailed reporting
"""

import pytest
import sys
import os
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any
import subprocess
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class PreferenceTestRunner:
    """Comprehensive test runner for preference processing tests"""
    
    def __init__(self):
        self.test_modules = [
            "tests/test_preference_end_to_end.py",
            "tests/test_preference_regression.py", 
            "tests/test_preference_load.py",
            "tests/test_preference_data_integrity.py",
            "tests/test_preference_user_acceptance.py"
        ]
        
        self.test_categories = {
            "end_to_end": "End-to-End Workflow Tests",
            "regression": "Regression Tests", 
            "load": "Load Testing",
            "data_integrity": "Data Integrity Tests",
            "user_acceptance": "User Acceptance Tests"
        }
        
        self.results = {}
        
    def run_test_module(self, module_path: str, category: str) -> Dict[str, Any]:
        """Run a specific test module and return results"""
        print(f"\n{'='*60}")
        print(f"Running {self.test_categories[category]}")
        print(f"Module: {module_path}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Run pytest with detailed output
            cmd = [
                sys.executable, "-m", "pytest", 
                module_path,
                "-v",  # Verbose output
                "--tb=short",  # Short traceback format
                "--durations=10",  # Show 10 slowest tests
                "--json-report",  # Generate JSON report
                f"--json-report-file=test_results_{category}.json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            execution_time = time.time() - start_time
            
            # Parse results
            test_results = {
                "category": category,
                "module": module_path,
                "execution_time": execution_time,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            # Try to load JSON report if available
            json_report_path = project_root / f"test_results_{category}.json"
            if json_report_path.exists():
                try:
                    with open(json_report_path, 'r') as f:
                        json_report = json.load(f)
                        test_results["detailed_results"] = json_report
                except Exception as e:
                    print(f"Warning: Could not parse JSON report: {e}")
            
            return test_results
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "category": category,
                "module": module_path,
                "execution_time": execution_time,
                "success": False,
                "error": str(e),
                "return_code": -1
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all preference-related tests"""
        print("🚀 Starting Comprehensive Preference Data Processing Tests")
        print(f"Test modules: {len(self.test_modules)}")
        print(f"Categories: {list(self.test_categories.keys())}")
        
        overall_start_time = time.time()
        
        # Run each test module
        for i, module_path in enumerate(self.test_modules):
            category = list(self.test_categories.keys())[i]
            
            print(f"\n📋 Progress: {i+1}/{len(self.test_modules)} - {self.test_categories[category]}")
            
            result = self.run_test_module(module_path, category)
            self.results[category] = result
            
            # Print immediate results
            if result["success"]:
                print(f"✅ {self.test_categories[category]} - PASSED ({result['execution_time']:.1f}s)")
            else:
                print(f"❌ {self.test_categories[category]} - FAILED ({result['execution_time']:.1f}s)")
                if result.get("stderr"):
                    print(f"Error: {result['stderr'][:200]}...")
        
        overall_execution_time = time.time() - overall_start_time
        
        # Generate comprehensive report
        report = self.generate_comprehensive_report(overall_execution_time)
        
        return report
    
    def generate_comprehensive_report(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        # Calculate summary statistics
        total_categories = len(self.results)
        passed_categories = sum(1 for result in self.results.values() if result["success"])
        failed_categories = total_categories - passed_categories
        
        # Detailed results by category
        category_details = {}
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for category, result in self.results.items():
            category_detail = {
                "name": self.test_categories[category],
                "success": result["success"],
                "execution_time": result["execution_time"],
                "return_code": result["return_code"]
            }
            
            # Extract test counts from detailed results if available
            if "detailed_results" in result:
                detailed = result["detailed_results"]
                if "summary" in detailed:
                    summary = detailed["summary"]
                    category_detail.update({
                        "total_tests": summary.get("total", 0),
                        "passed_tests": summary.get("passed", 0),
                        "failed_tests": summary.get("failed", 0),
                        "skipped_tests": summary.get("skipped", 0),
                        "error_tests": summary.get("error", 0)
                    })
                    
                    total_tests += summary.get("total", 0)
                    passed_tests += summary.get("passed", 0)
                    failed_tests += summary.get("failed", 0)
            
            category_details[category] = category_detail
        
        # Performance metrics
        performance_metrics = {
            "total_execution_time": total_time,
            "average_category_time": total_time / total_categories if total_categories > 0 else 0,
            "fastest_category": min(self.results.items(), key=lambda x: x[1]["execution_time"])[0] if self.results else None,
            "slowest_category": max(self.results.items(), key=lambda x: x[1]["execution_time"])[0] if self.results else None
        }
        
        # Quality assessment
        quality_assessment = {
            "overall_success_rate": passed_categories / total_categories if total_categories > 0 else 0,
            "test_success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "categories_passed": passed_categories,
            "categories_failed": failed_categories,
            "total_tests_run": total_tests,
            "tests_passed": passed_tests,
            "tests_failed": failed_tests
        }
        
        # Recommendations
        recommendations = self.generate_recommendations(category_details, quality_assessment)
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_categories": total_categories,
                "passed_categories": passed_categories,
                "failed_categories": failed_categories,
                "overall_success": failed_categories == 0
            },
            "category_details": category_details,
            "performance_metrics": performance_metrics,
            "quality_assessment": quality_assessment,
            "recommendations": recommendations
        }
        
        return report
    
    def generate_recommendations(self, category_details: Dict, quality_assessment: Dict) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Overall success rate recommendations
        if quality_assessment["overall_success_rate"] < 0.8:
            recommendations.append("🔴 CRITICAL: Less than 80% of test categories passed. Immediate attention required.")
        elif quality_assessment["overall_success_rate"] < 1.0:
            recommendations.append("🟡 WARNING: Some test categories failed. Review and fix failing tests.")
        else:
            recommendations.append("🟢 EXCELLENT: All test categories passed successfully.")
        
        # Performance recommendations
        total_time = sum(detail["execution_time"] for detail in category_details.values())
        if total_time > 300:  # 5 minutes
            recommendations.append("⏱️ PERFORMANCE: Tests taking longer than 5 minutes. Consider optimization.")
        elif total_time > 600:  # 10 minutes
            recommendations.append("🔴 PERFORMANCE: Tests taking longer than 10 minutes. Optimization required.")
        
        # Category-specific recommendations
        for category, details in category_details.items():
            if not details["success"]:
                category_name = details["name"]
                if category == "end_to_end":
                    recommendations.append(f"🔴 {category_name} failed: Core workflow issues detected. Priority fix required.")
                elif category == "regression":
                    recommendations.append(f"🟡 {category_name} failed: Existing functionality may be broken. Review changes.")
                elif category == "load":
                    recommendations.append(f"🟡 {category_name} failed: Performance issues under load. Optimization needed.")
                elif category == "data_integrity":
                    recommendations.append(f"🔴 {category_name} failed: Data quality issues detected. Critical fix required.")
                elif category == "user_acceptance":
                    recommendations.append(f"🟡 {category_name} failed: User experience issues. UX improvements needed.")
        
        # Test coverage recommendations
        if quality_assessment["total_tests_run"] < 50:
            recommendations.append("📊 COVERAGE: Consider adding more tests for better coverage.")
        elif quality_assessment["total_tests_run"] > 200:
            recommendations.append("📊 COVERAGE: Excellent test coverage achieved.")
        
        return recommendations
    
    def print_detailed_report(self, report: Dict[str, Any]):
        """Print detailed test report"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE PREFERENCE DATA PROCESSING TEST REPORT")
        print("="*80)
        
        # Summary
        summary = report["summary"]
        print(f"\n📊 SUMMARY:")
        print(f"   Total Categories: {summary['total_categories']}")
        print(f"   Passed: {summary['passed_categories']} ✅")
        print(f"   Failed: {summary['failed_categories']} ❌")
        print(f"   Overall Success: {'YES' if summary['overall_success'] else 'NO'} {'🎉' if summary['overall_success'] else '⚠️'}")
        
        # Category Details
        print(f"\n📋 CATEGORY RESULTS:")
        for category, details in report["category_details"].items():
            status = "✅ PASS" if details["success"] else "❌ FAIL"
            time_str = f"{details['execution_time']:.1f}s"
            print(f"   {details['name']:<30} {status:<8} ({time_str})")
            
            if "total_tests" in details:
                test_summary = f"{details['passed_tests']}/{details['total_tests']} tests passed"
                print(f"   {'':>30} {test_summary}")
        
        # Performance Metrics
        perf = report["performance_metrics"]
        print(f"\n⏱️ PERFORMANCE METRICS:")
        print(f"   Total Execution Time: {perf['total_execution_time']:.1f}s")
        print(f"   Average Category Time: {perf['average_category_time']:.1f}s")
        if perf['fastest_category']:
            print(f"   Fastest Category: {perf['fastest_category']}")
        if perf['slowest_category']:
            print(f"   Slowest Category: {perf['slowest_category']}")
        
        # Quality Assessment
        quality = report["quality_assessment"]
        print(f"\n🎯 QUALITY ASSESSMENT:")
        print(f"   Category Success Rate: {quality['overall_success_rate']:.1%}")
        if quality['total_tests_run'] > 0:
            print(f"   Test Success Rate: {quality['test_success_rate']:.1%}")
            print(f"   Total Tests Run: {quality['total_tests_run']}")
            print(f"   Tests Passed: {quality['tests_passed']}")
            print(f"   Tests Failed: {quality['tests_failed']}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        for recommendation in report["recommendations"]:
            print(f"   {recommendation}")
        
        print("\n" + "="*80)
        
        # Final verdict
        if summary["overall_success"]:
            print("🎉 VERDICT: All preference data processing tests PASSED!")
            print("   The system is ready for production deployment.")
        else:
            print("⚠️ VERDICT: Some tests FAILED!")
            print("   Review failed tests and fix issues before deployment.")
        
        print("="*80)
    
    def save_report(self, report: Dict[str, Any], filename: str = "preference_test_report.json"):
        """Save detailed report to file"""
        report_path = project_root / filename
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Detailed report saved to: {report_path}")
            
        except Exception as e:
            print(f"⚠️ Could not save report: {e}")


def main():
    """Main entry point for comprehensive preference testing"""
    
    print("🧪 Preference Data Processing - Comprehensive Test Suite")
    print("=" * 60)
    
    # Initialize test runner
    runner = PreferenceTestRunner()
    
    try:
        # Run all tests
        report = runner.run_all_tests()
        
        # Print detailed report
        runner.print_detailed_report(report)
        
        # Save report
        runner.save_report(report)
        
        # Return appropriate exit code
        return 0 if report["summary"]["overall_success"] else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)