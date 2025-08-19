"""
Example usage of PreferenceDataValidator

This example demonstrates how to use the PreferenceDataValidator to validate
preference query results and generate comprehensive validation reports.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl.preference_data_validator import PreferenceDataValidator
import json


def main():
    """Demonstrate PreferenceDataValidator usage"""
    
    # Initialize the validator
    validator = PreferenceDataValidator()
    
    print("=== Preference Data Validator Example ===\n")
    
    # Example 1: Valid data scenario
    print("1. Testing with valid preference data:")
    
    image_stats = [{
        "total_image_count": 120,
        "response_count": 98,
        "response_rate": 81.67
    }]
    
    preference_data = [
        {
            "preference_name": "창의적 표현",
            "question_count": 18,
            "response_rate": 83.5,
            "rank": 1,
            "description": "예술적이고 창의적인 활동을 선호하며, 자유로운 표현을 중시합니다."
        },
        {
            "preference_name": "체계적 분석",
            "question_count": 15,
            "response_rate": 78.2,
            "rank": 2,
            "description": "논리적이고 체계적인 분석을 통해 문제를 해결하는 것을 선호합니다."
        },
        {
            "preference_name": "대인 관계",
            "question_count": 12,
            "response_rate": 72.1,
            "rank": 3,
            "description": "사람들과의 상호작용과 협력을 통한 업무를 선호합니다."
        }
    ]
    
    preference_jobs = [
        {
            "preference_name": "창의적 표현",
            "preference_type": "rimg1",
            "jo_name": "그래픽 디자이너",
            "jo_outline": "시각적 콘텐츠와 그래픽 요소를 디자인하고 제작",
            "jo_mainbusiness": "웹사이트, 광고, 출판물 등의 시각적 디자인 작업",
            "majors": "시각디자인, 그래픽디자인, 멀티미디어디자인"
        },
        {
            "preference_name": "체계적 분석",
            "preference_type": "rimg2",
            "jo_name": "데이터 분석가",
            "jo_outline": "데이터를 수집, 분석하여 비즈니스 인사이트 도출",
            "jo_mainbusiness": "통계 분석, 데이터 모델링, 보고서 작성",
            "majors": "통계학, 데이터사이언스, 경영정보학"
        },
        {
            "preference_name": "대인 관계",
            "preference_type": "rimg3",
            "jo_name": "인사 관리자",
            "jo_outline": "조직의 인적자원 관리 및 개발 업무",
            "jo_mainbusiness": "채용, 교육, 성과관리, 조직문화 개선",
            "majors": "인사관리, 심리학, 경영학"
        }
    ]
    
    # Validate all queries
    results = validator.validate_all_preference_queries(
        image_stats_data=image_stats,
        preference_data=preference_data,
        preference_jobs_data=preference_jobs
    )
    
    # Generate report
    report = validator.generate_validation_report(results)
    
    print(f"Overall Valid: {report['overall_valid']}")
    print(f"Total Errors: {report['summary']['total_errors']}")
    print(f"Total Warnings: {report['summary']['total_warnings']}")
    print(f"Average Quality Score: {report['summary']['average_quality_score']:.2f}")
    
    if report['recommendations']:
        print("Recommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: Problematic data scenario
    print("2. Testing with problematic preference data:")
    
    problematic_image_stats = [{
        "total_image_count": 50,
        "response_count": 15,  # Low response count
        "response_rate": 25.0  # Low response rate
    }]
    
    problematic_preference_data = [
        {
            "preference_name": "A",  # Too short
            "question_count": 0,  # Zero questions
            "response_rate": 15.0,  # Very low response rate
            "rank": 1,
            "description": "Short"  # Too short description
        },
        {
            "preference_name": "Another Preference",
            "question_count": 8,
            "response_rate": 110.0,  # Invalid response rate
            "rank": 5,  # Invalid rank
            "description": "Valid description for this preference"
        }
    ]
    
    problematic_jobs = [
        {
            "preference_name": "Test",
            "preference_type": "invalid_type",  # Invalid type
            "jo_name": "X",  # Too short
            "jo_outline": "Short outline",  # Too short
            "jo_mainbusiness": "Brief",  # Too short
            "majors": ""  # Empty
        }
    ]
    
    # Validate problematic data
    problematic_results = validator.validate_all_preference_queries(
        image_stats_data=problematic_image_stats,
        preference_data=problematic_preference_data,
        preference_jobs_data=problematic_jobs
    )
    
    # Generate report
    problematic_report = validator.generate_validation_report(problematic_results)
    
    print(f"Overall Valid: {problematic_report['overall_valid']}")
    print(f"Total Errors: {problematic_report['summary']['total_errors']}")
    print(f"Total Warnings: {problematic_report['summary']['total_warnings']}")
    print(f"Average Quality Score: {problematic_report['summary']['average_quality_score']:.2f}")
    
    print("\nDetailed Issues:")
    for issue in problematic_report['issues']:
        severity = issue['severity'].upper()
        print(f"  [{severity}] {issue['query']} - {issue['field']}: {issue['message']}")
    
    print("\nRecommendations:")
    for rec in problematic_report['recommendations']:
        print(f"  - {rec}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 3: Individual query validation
    print("3. Testing individual query validation:")
    
    # Test image preference stats validation
    stats_result = validator.validate_image_preference_stats(image_stats)
    print(f"Image Stats Validation: {stats_result.get_summary()}")
    print(f"Quality Score: {stats_result.data_quality_score:.2f}")
    
    # Test preference data validation
    pref_result = validator.validate_preference_data(preference_data)
    print(f"Preference Data Validation: {pref_result.get_summary()}")
    print(f"Quality Score: {pref_result.data_quality_score:.2f}")
    
    # Test preference jobs validation
    jobs_result = validator.validate_preference_jobs(preference_jobs)
    print(f"Preference Jobs Validation: {jobs_result.get_summary()}")
    print(f"Quality Score: {jobs_result.data_quality_score:.2f}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 4: Empty data handling
    print("4. Testing empty data scenarios:")
    
    empty_results = validator.validate_all_preference_queries(
        image_stats_data=[],
        preference_data=[],
        preference_jobs_data=[]
    )
    
    empty_report = validator.generate_validation_report(empty_results)
    
    print(f"Empty Data Overall Valid: {empty_report['overall_valid']}")
    print("Query Status:")
    for query_name, query_result in empty_report['query_results'].items():
        print(f"  {query_name}: {query_result['data_status']} - {query_result['summary']}")
    
    print("\nEmpty Data Recommendations:")
    for rec in empty_report['recommendations']:
        print(f"  - {rec}")


if __name__ == "__main__":
    main()