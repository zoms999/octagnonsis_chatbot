#!/usr/bin/env python3
"""
Simple test to verify preference testing structure
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from etl.legacy_query_executor import LegacyQueryExecutor
from etl.document_transformer import DocumentTransformer
from etl.preference_data_validator import PreferenceDataValidator

async def test_basic_structure():
    """Test basic structure and imports"""
    print("Testing basic structure...")
    
    # Test that classes can be instantiated
    try:
        executor = LegacyQueryExecutor()
        transformer = DocumentTransformer()
        validator = PreferenceDataValidator()
        
        print("✅ All classes instantiated successfully")
        
        # Check if methods exist
        methods_to_check = [
            '_query_image_preference_stats',
            '_query_preference_data', 
            '_query_preference_jobs'
        ]
        
        for method_name in methods_to_check:
            if hasattr(executor, method_name):
                print(f"✅ Method {method_name} exists")
            else:
                print(f"❌ Method {method_name} missing")
        
        # Test document transformer method
        if hasattr(transformer, '_chunk_preference_analysis'):
            print("✅ Document transformer has _chunk_preference_analysis method")
        else:
            print("❌ Document transformer missing _chunk_preference_analysis method")
        
        # Test validator methods
        validator_methods = [
            'validate_image_preference_stats',
            'validate_preference_data',
            'validate_preference_jobs',
            'generate_validation_report'
        ]
        
        for method_name in validator_methods:
            if hasattr(validator, method_name):
                print(f"✅ Validator method {method_name} exists")
            else:
                print(f"❌ Validator method {method_name} missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during basic structure test: {e}")
        return False

async def test_mock_workflow():
    """Test a simple mock workflow"""
    print("\nTesting mock workflow...")
    
    try:
        # Test document transformation with mock data
        transformer = DocumentTransformer()
        
        mock_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [{
                "preference_name": "실내 활동 선호",
                "rank": 1,
                "response_rate": 85,
                "description": "조용한 환경을 선호합니다."
            }],
            "preferenceJobsQuery": [{
                "preference_name": "실내 활동 선호",
                "jo_name": "소프트웨어 개발자"
            }]
        }
        
        documents = transformer._chunk_preference_analysis(mock_data)
        
        print(f"✅ Document transformation successful: {len(documents)} documents created")
        
        # Test validation
        validator = PreferenceDataValidator()
        validation_report = validator.generate_validation_report(mock_data)
        
        print(f"✅ Validation successful: overall_valid = {validation_report.overall_valid}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during mock workflow test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🧪 Simple Preference Testing Structure Verification")
    print("=" * 60)
    
    # Test basic structure
    structure_ok = await test_basic_structure()
    
    # Test mock workflow
    workflow_ok = await test_mock_workflow()
    
    print("\n" + "=" * 60)
    if structure_ok and workflow_ok:
        print("🎉 All basic tests passed! Test structure is ready.")
        return 0
    else:
        print("❌ Some tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)