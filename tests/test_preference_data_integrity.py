"""
Data integrity tests for preference document quality validation
Tests data consistency, accuracy, and quality throughout the preference processing pipeline
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from typing import Dict, List, Any, Set
import json
import hashlib

from etl.legacy_query_executor import LegacyQueryExecutor, QueryResult
from etl.document_transformer import DocumentTransformer, TransformedDocument
from etl.preference_data_validator import PreferenceDataValidator, ValidationResult
from database.models import DocumentType


class TestPreferenceDataIntegrity:
    """Data integrity tests for preference document processing"""
    
    def test_data_consistency_through_pipeline(self):
        """Test that data remains consistent throughout the processing pipeline"""
        
        # Original source data
        source_data = {
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
                    "jo_mainbusiness": "브랜드 및 광고 디자인",
                    "majors": "시각디자인, 산업디자인"
                }
            ]
        }
        
        # Step 1: Transform documents
        transformer = DocumentTransformer()
        documents = transformer._chunk_preference_analysis(source_data)
        
        # Step 2: Verify data consistency
        
        # Check stats data consistency
        stats_docs = [doc for doc in documents if doc.metadata.get("sub_type") == "test_stats"]
        assert len(stats_docs) == 1
        stats_doc = stats_docs[0]
        
        # Verify stats values match source
        assert stats_doc.content["total_images"] == source_data["imagePreferenceStatsQuery"][0]["total_image_count"]
        assert stats_doc.content["completed_images"] == source_data["imagePreferenceStatsQuery"][0]["response_count"]
        assert stats_doc.content["completion_rate"] == source_data["imagePreferenceStatsQuery"][0]["response_rate"]
        
        # Check preference data consistency
        pref_docs = [doc for doc in documents if doc.metadata.get("sub_type", "").startswith("preference_")]
        assert len(pref_docs) == 2  # Should have 2 preference documents
        
        # Verify preference data matches source
        source_prefs = {pref["preference_name"]: pref for pref in source_data["preferenceDataQuery"]}
        
        for pref_doc in pref_docs:
            pref_name = pref_doc.content["preference_name"]
            assert pref_name in source_prefs
            
            source_pref = source_prefs[pref_name]
            assert pref_doc.content["rank"] == source_pref["rank"]
            assert pref_doc.content["response_rate"] == source_pref["response_rate"]
            assert pref_doc.content["description"] == source_pref["description"]
        
        # Check job data consistency
        job_docs = [doc for doc in documents if doc.metadata.get("sub_type", "").startswith("jobs_")]
        job_detail_docs = [doc for doc in job_docs if doc.metadata.get("sub_type") != "jobs_overview"]
        
        # Verify job data matches source
        source_jobs = {}
        for job in source_data["preferenceJobsQuery"]:
            pref_name = job["preference_name"]
            if pref_name not in source_jobs:
                source_jobs[pref_name] = []
            source_jobs[pref_name].append(job)
        
        for job_doc in job_detail_docs:
            pref_name = job_doc.content["preference_name"]
            if pref_name in source_jobs:
                source_job_names = [job["jo_name"] for job in source_jobs[pref_name]]
                doc_job_names = [job["name"] for job in job_doc.content["jobs"]]
                
                # All source jobs should be present in document
                for source_job_name in source_job_names:
                    assert source_job_name in doc_job_names

    def test_data_completeness_validation(self):
        """Test that all required data fields are present and complete"""
        
        transformer = DocumentTransformer()
        
        # Test with complete data
        complete_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [{
                "preference_name": "실내 활동 선호",
                "question_count": 15,
                "response_rate": 85,
                "rank": 1,
                "description": "조용한 환경을 선호합니다."
            }],
            "preferenceJobsQuery": [{
                "preference_name": "실내 활동 선호",
                "preference_type": "rimg1",
                "jo_name": "소프트웨어 개발자",
                "jo_outline": "프로그램 개발",
                "jo_mainbusiness": "소프트웨어 설계",
                "majors": "컴퓨터공학"
            }]
        }
        
        documents = transformer._chunk_preference_analysis(complete_data)
        
        # Verify all documents have required fields
        for doc in documents:
            # Basic document structure
            assert hasattr(doc, 'doc_type')
            assert hasattr(doc, 'content')
            assert hasattr(doc, 'summary_text')
            assert hasattr(doc, 'metadata')
            
            # Document type should be correct
            assert doc.doc_type == "PREFERENCE_ANALYSIS"
            
            # Content should not be empty
            assert doc.content is not None
            assert len(doc.content) > 0
            
            # Summary should not be empty
            assert doc.summary_text is not None
            assert len(doc.summary_text.strip()) > 0
            
            # Metadata should have required fields
            assert "sub_type" in doc.metadata
            assert "created_at" in doc.metadata
            assert "completion_level" in doc.metadata
            
            # Sub-type should be valid
            valid_subtypes = [
                "test_stats", "preferences_overview", "partial_stats", "partial_available",
                "unavailable"
            ]
            sub_type = doc.metadata["sub_type"]
            assert (sub_type in valid_subtypes or 
                   sub_type.startswith("preference_") or 
                   sub_type.startswith("jobs_"))

    def test_data_accuracy_validation(self):
        """Test that calculated and derived data is accurate"""
        
        transformer = DocumentTransformer()
        
        # Test data with specific values for accuracy checking
        test_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 150,
                "response_count": 120,
                "response_rate": 80  # Should match 120/150 * 100
            }],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 90,
                    "question_count": 20
                },
                {
                    "preference_name": "야외 활동 선호",
                    "rank": 2,
                    "response_rate": 75,
                    "question_count": 15
                }
            ],
            "preferenceJobsQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "jo_name": "개발자"
                },
                {
                    "preference_name": "실내 활동 선호",
                    "jo_name": "분석가"
                },
                {
                    "preference_name": "야외 활동 선호",
                    "jo_name": "건축가"
                }
            ]
        }
        
        documents = transformer._chunk_preference_analysis(test_data)
        
        # Verify stats calculations
        stats_docs = [doc for doc in documents if doc.metadata.get("sub_type") == "test_stats"]
        if stats_docs:
            stats_doc = stats_docs[0]
            
            # Verify completion rate calculation
            expected_rate = (120 / 150) * 100
            assert abs(stats_doc.content["completion_rate"] - expected_rate) < 0.1
            
            # Verify completion status based on rate
            if stats_doc.content["completion_rate"] >= 80:
                assert stats_doc.content["completion_status"] == "완료"
            elif stats_doc.content["completion_rate"] >= 50:
                assert stats_doc.content["completion_status"] == "부분완료"
            else:
                assert stats_doc.content["completion_status"] == "미완료"
        
        # Verify preference ranking accuracy
        pref_docs = [doc for doc in documents if doc.metadata.get("sub_type", "").startswith("preference_")]
        
        # Should be sorted by rank
        pref_ranks = []
        for pref_doc in pref_docs:
            rank = pref_doc.content["rank"]
            pref_ranks.append(rank)
        
        assert pref_ranks == sorted(pref_ranks)  # Should be in ascending order
        
        # Verify preference strength calculation
        for pref_doc in pref_docs:
            rank = pref_doc.content["rank"]
            strength = pref_doc.content.get("preference_strength", "")
            
            if rank == 1:
                assert strength == "강함"
            elif rank == 2:
                assert strength == "보통"
            else:
                assert strength in ["약함", "보통"]
        
        # Verify job count accuracy
        job_docs = [doc for doc in documents if doc.metadata.get("sub_type", "").startswith("jobs_")]
        job_detail_docs = [doc for doc in job_docs if doc.metadata.get("sub_type") != "jobs_overview"]
        
        # Count jobs per preference in source data
        source_job_counts = {}
        for job in test_data["preferenceJobsQuery"]:
            pref_name = job["preference_name"]
            source_job_counts[pref_name] = source_job_counts.get(pref_name, 0) + 1
        
        # Verify job counts in documents
        for job_doc in job_detail_docs:
            pref_name = job_doc.content["preference_name"]
            if pref_name in source_job_counts:
                expected_count = source_job_counts[pref_name]
                actual_count = len(job_doc.content["jobs"])
                assert actual_count == expected_count

    def test_data_quality_metrics(self):
        """Test data quality metrics and scoring"""
        
        validator = PreferenceDataValidator()
        
        # Test high quality data
        high_quality_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 110,
                "response_rate": 92
            }],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 95,
                    "question_count": 20,
                    "description": "상세한 설명이 포함된 선호도입니다."
                },
                {
                    "preference_name": "창의적 활동 선호",
                    "rank": 2,
                    "response_rate": 88,
                    "question_count": 18,
                    "description": "창의성을 중시하는 활동을 선호합니다."
                }
            ],
            "preferenceJobsQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "preference_type": "rimg1",
                    "jo_name": "소프트웨어 개발자",
                    "jo_outline": "상세한 직업 개요",
                    "jo_mainbusiness": "주요 업무 설명",
                    "majors": "관련 전공 정보"
                }
            ]
        }
        
        high_quality_report = validator.generate_validation_report(high_quality_data)
        
        # High quality data should pass all validations
        assert high_quality_report.overall_valid == True
        assert high_quality_report.stats_validation.is_valid == True
        assert high_quality_report.preferences_validation.is_valid == True
        assert high_quality_report.jobs_validation.is_valid == True
        
        # Test low quality data
        low_quality_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 30,  # Low response rate
                "response_rate": 25
            }],
            "preferenceDataQuery": [
                {
                    "preference_name": "",  # Empty name
                    "rank": 1,
                    "response_rate": 45,  # Low response rate
                    "description": ""  # Empty description
                },
                {
                    "preference_name": "선호도",  # Minimal name
                    "rank": None,  # Missing rank
                    "response_rate": None  # Missing response rate
                }
            ],
            "preferenceJobsQuery": [
                {
                    "preference_name": None,  # Missing name
                    "jo_name": "",  # Empty job name
                    "jo_outline": None  # Missing outline
                }
            ]
        }
        
        low_quality_report = validator.generate_validation_report(low_quality_data)
        
        # Low quality data should fail validations
        assert low_quality_report.overall_valid == False
        assert low_quality_report.stats_validation.is_valid == False  # Low response rate
        assert low_quality_report.preferences_validation.is_valid == False  # Missing/invalid data
        assert low_quality_report.jobs_validation.is_valid == False  # Missing/invalid data

    def test_data_integrity_with_edge_cases(self):
        """Test data integrity with edge cases and boundary conditions"""
        
        transformer = DocumentTransformer()
        
        # Edge case scenarios
        edge_cases = [
            # Zero values
            {
                "imagePreferenceStatsQuery": [{
                    "total_image_count": 0,
                    "response_count": 0,
                    "response_rate": 0
                }],
                "preferenceDataQuery": [],
                "preferenceJobsQuery": []
            },
            # Maximum values
            {
                "imagePreferenceStatsQuery": [{
                    "total_image_count": 999999,
                    "response_count": 999999,
                    "response_rate": 100
                }],
                "preferenceDataQuery": [{
                    "preference_name": "A" * 1000,  # Very long name
                    "rank": 999,
                    "response_rate": 100
                }],
                "preferenceJobsQuery": []
            },
            # Negative values (invalid)
            {
                "imagePreferenceStatsQuery": [{
                    "total_image_count": -10,
                    "response_count": -5,
                    "response_rate": -20
                }],
                "preferenceDataQuery": [{
                    "preference_name": "테스트",
                    "rank": -1,
                    "response_rate": -50
                }],
                "preferenceJobsQuery": []
            },
            # Inconsistent data
            {
                "imagePreferenceStatsQuery": [{
                    "total_image_count": 100,
                    "response_count": 150,  # More responses than total
                    "response_rate": 150
                }],
                "preferenceDataQuery": [{
                    "preference_name": "테스트",
                    "rank": 1,
                    "response_rate": 200  # Invalid percentage
                }],
                "preferenceJobsQuery": []
            }
        ]
        
        for i, edge_case in enumerate(edge_cases):
            # Should handle edge cases gracefully without crashing
            documents = transformer._chunk_preference_analysis(edge_case)
            
            # Should always create at least one document (fallback if needed)
            assert len(documents) >= 1
            
            # All documents should have valid structure
            for doc in documents:
                assert doc.doc_type == "PREFERENCE_ANALYSIS"
                assert doc.content is not None
                assert doc.summary_text is not None
                assert doc.metadata is not None
                assert "sub_type" in doc.metadata
            
            print(f"Edge case {i+1} handled successfully: {len(documents)} documents created")

    def test_data_transformation_reversibility(self):
        """Test that key data can be extracted back from transformed documents"""
        
        transformer = DocumentTransformer()
        
        # Original data
        original_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 85,
                    "description": "조용한 환경을 선호합니다."
                },
                {
                    "preference_name": "창의적 활동 선호",
                    "rank": 2,
                    "response_rate": 78,
                    "description": "창의적 사고를 중시합니다."
                }
            ],
            "preferenceJobsQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "jo_name": "소프트웨어 개발자"
                },
                {
                    "preference_name": "창의적 활동 선호",
                    "jo_name": "그래픽 디자이너"
                }
            ]
        }
        
        # Transform to documents
        documents = transformer._chunk_preference_analysis(original_data)
        
        # Extract data back from documents
        extracted_data = {
            "stats": {},
            "preferences": [],
            "jobs": []
        }
        
        for doc in documents:
            sub_type = doc.metadata.get("sub_type")
            
            if sub_type == "test_stats":
                extracted_data["stats"] = {
                    "total_images": doc.content["total_images"],
                    "completed_images": doc.content["completed_images"],
                    "completion_rate": doc.content["completion_rate"]
                }
            elif sub_type.startswith("preference_"):
                extracted_data["preferences"].append({
                    "name": doc.content["preference_name"],
                    "rank": doc.content["rank"],
                    "response_rate": doc.content["response_rate"],
                    "description": doc.content["description"]
                })
            elif sub_type.startswith("jobs_") and sub_type != "jobs_overview":
                for job in doc.content["jobs"]:
                    extracted_data["jobs"].append({
                        "preference_name": doc.content["preference_name"],
                        "job_name": job["name"]
                    })
        
        # Verify extracted data matches original
        
        # Stats verification
        original_stats = original_data["imagePreferenceStatsQuery"][0]
        assert extracted_data["stats"]["total_images"] == original_stats["total_image_count"]
        assert extracted_data["stats"]["completed_images"] == original_stats["response_count"]
        assert extracted_data["stats"]["completion_rate"] == original_stats["response_rate"]
        
        # Preferences verification
        assert len(extracted_data["preferences"]) == len(original_data["preferenceDataQuery"])
        
        for original_pref in original_data["preferenceDataQuery"]:
            matching_extracted = next(
                (p for p in extracted_data["preferences"] 
                 if p["name"] == original_pref["preference_name"]), 
                None
            )
            assert matching_extracted is not None
            assert matching_extracted["rank"] == original_pref["rank"]
            assert matching_extracted["response_rate"] == original_pref["response_rate"]
            assert matching_extracted["description"] == original_pref["description"]
        
        # Jobs verification
        original_job_names = [job["jo_name"] for job in original_data["preferenceJobsQuery"]]
        extracted_job_names = [job["job_name"] for job in extracted_data["jobs"]]
        
        for original_job_name in original_job_names:
            assert original_job_name in extracted_job_names

    def test_data_integrity_checksums(self):
        """Test data integrity using checksums and hashing"""
        
        transformer = DocumentTransformer()
        
        # Create test data
        test_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [{
                "preference_name": "실내 활동 선호",
                "rank": 1,
                "response_rate": 85
            }],
            "preferenceJobsQuery": [{
                "preference_name": "실내 활동 선호",
                "jo_name": "소프트웨어 개발자"
            }]
        }
        
        # Calculate checksum of original data
        original_checksum = hashlib.md5(
            json.dumps(test_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Transform documents
        documents = transformer._chunk_preference_analysis(test_data)
        
        # Add checksums to document metadata (simulating enhanced transformer)
        for doc in documents:
            doc.metadata["data_checksum"] = original_checksum
            doc.metadata["doc_checksum"] = hashlib.md5(
                json.dumps(doc.content, sort_keys=True).encode()
            ).hexdigest()
        
        # Verify checksums are present and valid
        for doc in documents:
            assert "data_checksum" in doc.metadata
            assert "doc_checksum" in doc.metadata
            assert doc.metadata["data_checksum"] == original_checksum
            assert len(doc.metadata["doc_checksum"]) == 32  # MD5 hash length
        
        # Test checksum validation after modification
        modified_doc = documents[0]
        original_doc_checksum = modified_doc.metadata["doc_checksum"]
        
        # Modify document content
        modified_doc.content["test_modification"] = "modified"
        
        # Recalculate checksum
        new_checksum = hashlib.md5(
            json.dumps(modified_doc.content, sort_keys=True).encode()
        ).hexdigest()
        
        # Checksums should be different
        assert new_checksum != original_doc_checksum

    def test_data_integrity_cross_validation(self):
        """Test cross-validation between different data sources"""
        
        transformer = DocumentTransformer()
        validator = PreferenceDataValidator()
        
        # Test data with cross-references
        test_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 85
                },
                {
                    "preference_name": "창의적 활동 선호",
                    "rank": 2,
                    "response_rate": 78
                }
            ],
            "preferenceJobsQuery": [
                {
                    "preference_name": "실내 활동 선호",  # Should match preference data
                    "jo_name": "소프트웨어 개발자"
                },
                {
                    "preference_name": "창의적 활동 선호",  # Should match preference data
                    "jo_name": "그래픽 디자이너"
                },
                {
                    "preference_name": "존재하지 않는 선호도",  # Should not match
                    "jo_name": "테스트 직업"
                }
            ]
        }
        
        # Validate cross-references
        validation_report = validator.generate_validation_report(test_data)
        
        # Transform documents
        documents = transformer._chunk_preference_analysis(test_data)
        
        # Extract preference names from different sources
        preference_names_from_prefs = set()
        preference_names_from_jobs = set()
        
        for doc in documents:
            sub_type = doc.metadata.get("sub_type")
            
            if sub_type.startswith("preference_"):
                preference_names_from_prefs.add(doc.content["preference_name"])
            elif sub_type.startswith("jobs_") and sub_type != "jobs_overview":
                preference_names_from_jobs.add(doc.content["preference_name"])
        
        # Verify cross-references
        valid_preferences = {"실내 활동 선호", "창의적 활동 선호"}
        
        # All preference names from preference documents should be valid
        assert preference_names_from_prefs.issubset(valid_preferences)
        
        # Job documents should only reference valid preferences (or use default names)
        for pref_name in preference_names_from_jobs:
            assert (pref_name in valid_preferences or 
                   pref_name.startswith("선호도 "))  # Default naming pattern
        
        print(f"Cross-validation completed:")
        print(f"  Valid preferences: {valid_preferences}")
        print(f"  Preferences in pref docs: {preference_names_from_prefs}")
        print(f"  Preferences in job docs: {preference_names_from_jobs}")

    def test_data_integrity_temporal_consistency(self):
        """Test temporal consistency of data processing"""
        
        transformer = DocumentTransformer()
        
        # Mock consistent timestamp
        fixed_timestamp = "2024-01-15T10:30:00"
        
        with patch('etl.document_transformer.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = fixed_timestamp
            
            test_data = {
                "imagePreferenceStatsQuery": [{
                    "total_image_count": 120,
                    "response_count": 96,
                    "response_rate": 80
                }],
                "preferenceDataQuery": [{
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 85
                }],
                "preferenceJobsQuery": []
            }
            
            # Transform documents multiple times
            documents_batch1 = transformer._chunk_preference_analysis(test_data)
            documents_batch2 = transformer._chunk_preference_analysis(test_data)
            
            # All documents should have the same timestamp
            timestamps_batch1 = [doc.metadata.get("created_at") for doc in documents_batch1]
            timestamps_batch2 = [doc.metadata.get("created_at") for doc in documents_batch2]
            
            # Within each batch, timestamps should be consistent
            assert all(ts == fixed_timestamp for ts in timestamps_batch1)
            assert all(ts == fixed_timestamp for ts in timestamps_batch2)
            
            # Between batches, timestamps should be the same (since we mocked the time)
            assert timestamps_batch1 == timestamps_batch2

    def test_data_integrity_unicode_handling(self):
        """Test proper handling of Unicode and special characters"""
        
        transformer = DocumentTransformer()
        
        # Test data with various Unicode characters
        unicode_test_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [
                {
                    "preference_name": "한글 선호도 테스트 🎨",
                    "rank": 1,
                    "response_rate": 85,
                    "description": "특수문자 포함: @#$%^&*()_+-=[]{}|;':\",./<>?"
                },
                {
                    "preference_name": "English Preference Test 🔬",
                    "rank": 2,
                    "response_rate": 78,
                    "description": "Mixed 한글 and English with émojis 🌟"
                },
                {
                    "preference_name": "数字测试 123 ñáéíóú",
                    "rank": 3,
                    "response_rate": 70,
                    "description": "Números y acentos: 1234567890"
                }
            ],
            "preferenceJobsQuery": [
                {
                    "preference_name": "한글 선호도 테스트 🎨",
                    "jo_name": "소프트웨어 개발자 👨‍💻",
                    "jo_outline": "프로그래밍 및 시스템 개발",
                    "majors": "컴퓨터공학, 소프트웨어공학"
                }
            ]
        }
        
        # Transform documents
        documents = transformer._chunk_preference_analysis(unicode_test_data)
        
        # Verify Unicode handling
        for doc in documents:
            # Content should preserve Unicode characters
            content_str = json.dumps(doc.content, ensure_ascii=False)
            summary_str = doc.summary_text
            
            # Should contain original Unicode characters
            if doc.metadata.get("sub_type", "").startswith("preference_"):
                pref_name = doc.content["preference_name"]
                
                # Verify specific Unicode preservation
                if "🎨" in pref_name:
                    assert "🎨" in content_str
                    assert "🎨" in summary_str
                
                if "émojis" in doc.content.get("description", ""):
                    assert "émojis" in content_str
                
                if "数字测试" in pref_name:
                    assert "数字测试" in content_str
            
            # Verify no encoding errors
            assert "\\u" not in content_str  # Should not have escaped Unicode
            assert len(summary_str.encode('utf-8')) >= len(summary_str)  # UTF-8 encoding works
        
        print("Unicode integrity test passed - all special characters preserved")