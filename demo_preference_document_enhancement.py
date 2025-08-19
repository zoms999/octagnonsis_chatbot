#!/usr/bin/env python3
"""
Demonstration script for enhanced preference document creation
Shows the improvements made to handle partial data and create informative fallback documents
"""

import json
from etl.document_transformer import DocumentTransformer


def print_documents(documents, title):
    """Helper function to print documents in a readable format"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Created {len(documents)} documents:")
    
    for i, doc in enumerate(documents, 1):
        print(f"\n--- Document {i}: {doc.metadata.get('sub_type', 'unknown')} ---")
        print(f"Summary: {doc.summary_text}")
        print(f"Completion Level: {doc.metadata.get('completion_level', 'unknown')}")
        
        # Show key content highlights
        if doc.metadata.get('sub_type') == 'test_stats':
            print(f"Response Rate: {doc.content.get('response_rate', 'N/A')}%")
            print(f"Status: {doc.content.get('completion_status', 'N/A')}")
            print(f"Interpretation: {doc.content.get('interpretation', 'N/A')[:100]}...")
        elif doc.metadata.get('sub_type', '').startswith('preference_'):
            print(f"Preference: {doc.content.get('preference_name', 'N/A')}")
            print(f"Rank: {doc.content.get('rank', 'N/A')}")
            print(f"Strength: {doc.content.get('preference_strength', 'N/A')}")
        elif doc.metadata.get('sub_type', '').startswith('jobs_'):
            print(f"Job Count: {doc.content.get('job_count', 'N/A')}")
            print(f"Top Jobs: {', '.join(doc.content.get('top_jobs', [])[:3])}")
        elif doc.metadata.get('sub_type') == 'unavailable':
            print(f"Missing Components: {len(doc.content.get('missing_components', []))}")
            print(f"Has Alternatives: {doc.metadata.get('has_alternatives', False)}")


def demo_complete_preference_data():
    """Demonstrate document creation with complete preference data"""
    transformer = DocumentTransformer()
    
    query_results = {
        "imagePreferenceStatsQuery": [{
            "total_image_count": 120,
            "response_count": 96,
            "response_rate": 80
        }],
        "preferenceDataQuery": [
            {
                "preference_name": "실내 활동 선호",
                "question_count": 15,
                "response_rate": 85,
                "rank": 1,
                "description": "조용하고 집중할 수 있는 환경을 선호합니다."
            },
            {
                "preference_name": "창의적 활동 선호",
                "question_count": 12,
                "response_rate": 78,
                "rank": 2,
                "description": "새로운 아이디어를 만들어내는 활동을 좋아합니다."
            }
        ],
        "preferenceJobsQuery": [
            {
                "preference_name": "실내 활동 선호",
                "preference_type": "rimg1",
                "jo_name": "소프트웨어 개발자",
                "jo_outline": "컴퓨터 프로그램 개발",
                "jo_mainbusiness": "소프트웨어 설계 및 개발",
                "majors": "컴퓨터공학, 소프트웨어공학"
            },
            {
                "preference_name": "창의적 활동 선호",
                "preference_type": "rimg2",
                "jo_name": "그래픽 디자이너",
                "jo_outline": "시각 디자인 작업",
                "jo_mainbusiness": "광고 및 브랜딩 디자인",
                "majors": "시각디자인, 산업디자인"
            }
        ]
    }
    
    documents = transformer._chunk_preference_analysis(query_results)
    print_documents(documents, "SCENARIO 1: Complete Preference Data")


def demo_partial_preference_data():
    """Demonstrate document creation with partial preference data"""
    transformer = DocumentTransformer()
    
    query_results = {
        "imagePreferenceStatsQuery": [],  # No stats available
        "preferenceDataQuery": [
            {
                "preference_name": "실내 활동 선호",
                "question_count": 15,
                "response_rate": 85,
                "rank": 1,
                "description": "조용하고 집중할 수 있는 환경을 선호합니다."
            }
        ],
        "preferenceJobsQuery": []  # No job recommendations available
    }
    
    documents = transformer._chunk_preference_analysis(query_results)
    print_documents(documents, "SCENARIO 2: Partial Preference Data (Only Preferences)")


def demo_low_quality_data():
    """Demonstrate handling of low-quality preference data"""
    transformer = DocumentTransformer()
    
    query_results = {
        "imagePreferenceStatsQuery": [{
            "total_image_count": 120,
            "response_count": 24,  # Very low response rate
            "response_rate": 20
        }],
        "preferenceDataQuery": [
            {
                "preference_name": "실내 활동 선호",
                "question_count": 15,
                "response_rate": 30,  # Low response rate
                "rank": 1,
                "description": "조용하고 집중할 수 있는 환경을 선호합니다."
            }
        ],
        "preferenceJobsQuery": []
    }
    
    documents = transformer._chunk_preference_analysis(query_results)
    print_documents(documents, "SCENARIO 3: Low Quality Data (Low Response Rates)")


def demo_no_preference_data():
    """Demonstrate fallback document creation when no preference data is available"""
    transformer = DocumentTransformer()
    
    query_results = {
        "imagePreferenceStatsQuery": [],
        "preferenceDataQuery": [],
        "preferenceJobsQuery": []
    }
    
    documents = transformer._chunk_preference_analysis(query_results)
    print_documents(documents, "SCENARIO 4: No Preference Data (Fallback)")


def demo_malformed_data():
    """Demonstrate resilience to malformed data"""
    transformer = DocumentTransformer()
    
    query_results = {
        "imagePreferenceStatsQuery": [{}],  # Empty dict
        "preferenceDataQuery": [
            {"preference_name": "실내 활동 선호", "rank": 1},  # Valid
            {"preference_name": None, "rank": None},  # Invalid
            {"preference_name": "", "rank": 2}  # Empty name
        ],
        "preferenceJobsQuery": [
            {"jo_name": "Developer"}  # Missing preference_name
        ]
    }
    
    documents = transformer._chunk_preference_analysis(query_results)
    print_documents(documents, "SCENARIO 5: Malformed Data (Error Resilience)")


def main():
    """Run all demonstration scenarios"""
    print("Enhanced Preference Document Creation Demonstration")
    print("This shows the improvements made to handle various data scenarios")
    
    # Run all scenarios
    demo_complete_preference_data()
    demo_partial_preference_data()
    demo_low_quality_data()
    demo_no_preference_data()
    demo_malformed_data()
    
    print(f"\n{'='*60}")
    print("SUMMARY OF IMPROVEMENTS")
    print(f"{'='*60}")
    print("✅ Separate document creation for each preference data type")
    print("✅ Intelligent fallback documents with helpful explanations")
    print("✅ Response rate interpretation and quality assessment")
    print("✅ Graceful handling of partial and missing data")
    print("✅ Error resilience for malformed data")
    print("✅ Informative content instead of generic 'data not ready' messages")
    print("✅ Proper grouping and analysis of preference-based job recommendations")
    print("✅ Comprehensive metadata for better search and retrieval")


if __name__ == "__main__":
    main()