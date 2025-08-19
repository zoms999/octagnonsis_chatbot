"""
Unit tests for PreferenceDataValidator

Tests all validation scenarios and edge cases for preference query results.
"""

import pytest
from typing import Dict, Any, List
from etl.preference_data_validator import (
    PreferenceDataValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity
)


class TestPreferenceDataValidator:
    """Test suite for PreferenceDataValidator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = PreferenceDataValidator()
    
    # ==================== Image Preference Stats Tests ====================
    
    def test_validate_image_preference_stats_valid_data(self):
        """Test validation with valid image preference statistics"""
        data = [{
            "total_image_count": 100,
            "response_count": 85,
            "response_rate": 85.0
        }]
        
        result = self.validator.validate_image_preference_stats(data)
        
        assert result.is_valid
        assert result.error_count == 0
        assert result.empty_vs_invalid == "valid"
        assert result.data_quality_score > 0.8
    
    def test_validate_image_preference_stats_empty_data(self):
        """Test validation with empty data"""
        data = []
        
        result = self.validator.validate_image_preference_stats(data)
        
        assert result.empty_vs_invalid == "empty"
        assert result.warning_count == 1
        assert any("No image preference statistics data found" in issue.message 
                  for issue in result.issues)
    
    def test_validate_image_preference_stats_multiple_rows(self):
        """Test validation with incorrect number of rows"""
        data = [
            {"total_image_count": 100, "response_count": 85, "response_rate": 85.0},
            {"total_image_count": 50, "response_count": 40, "response_rate": 80.0}
        ]
        
        result = self.validator.validate_image_preference_stats(data)
        
        assert not result.is_valid
        assert result.error_count >= 1
        assert any("Expected exactly 1 row" in issue.message for issue in result.issues)
    
    def test_validate_image_preference_stats_missing_fields(self):
        """Test validation with missing required fields"""
        data = [{"total_image_count": 100}]  # Missing response_count and response_rate
        
        result = self.validator.validate_image_preference_stats(data)
        
        assert not result.is_valid
        assert result.error_count >= 2
        field_errors = [issue.field_name for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert "response_count" in field_errors
        assert "response_rate" in field_errors
    
    def test_validate_image_preference_stats_null_values(self):
        """Test validation with null values"""
        data = [{
            "total_image_count": None,
            "response_count": None,
            "response_rate": None
        }]
        
        result = self.validator.validate_image_preference_stats(data)
        
        assert result.warning_count >= 3
        null_warnings = [issue for issue in result.issues if "null value" in issue.message]
        assert len(null_warnings) == 3
    
    def test_validate_image_preference_stats_invalid_ranges(self):
        """Test validation with values outside valid ranges"""
        data = [{
            "total_image_count": -10,  # Negative
            "response_count": 150,     # Greater than total
            "response_rate": 120.0     # > 100%
        }]
        
        result = self.validator.validate_image_preference_stats(data)
        
        assert not result.is_valid
        assert result.error_count >= 3
        
        # Check specific error types
        error_messages = [issue.message for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert any("non-negative number" in msg for msg in error_messages)
        assert any("exceeds total count" in msg for msg in error_messages)
        assert any("outside valid range 0-100" in msg for msg in error_messages)
    
    def test_validate_image_preference_stats_low_response_rate(self):
        """Test validation with low response rate"""
        data = [{
            "total_image_count": 100,
            "response_count": 20,
            "response_rate": 20.0
        }]
        
        result = self.validator.validate_image_preference_stats(data)
        
        assert result.is_valid  # Still valid, but with warning
        assert result.warning_count >= 1
        assert any("Low response rate" in issue.message for issue in result.issues)
    
    def test_validate_image_preference_stats_calculation_mismatch(self):
        """Test validation with mismatched calculated response rate"""
        data = [{
            "total_image_count": 100,
            "response_count": 80,
            "response_rate": 90.0  # Should be 80%
        }]
        
        result = self.validator.validate_image_preference_stats(data)
        
        assert result.warning_count >= 1
        assert any("doesn't match calculated rate" in issue.message for issue in result.issues)
    
    # ==================== Preference Data Tests ====================
    
    def test_validate_preference_data_valid_data(self):
        """Test validation with valid preference data"""
        data = [
            {
                "preference_name": "Visual Arts",
                "question_count": 15,
                "response_rate": 85.0,
                "rank": 1,
                "description": "Strong preference for visual and artistic activities"
            },
            {
                "preference_name": "Technical Skills",
                "question_count": 12,
                "response_rate": 78.0,
                "rank": 2,
                "description": "Good aptitude for technical and analytical tasks"
            },
            {
                "preference_name": "Social Interaction",
                "question_count": 10,
                "response_rate": 65.0,
                "rank": 3,
                "description": "Moderate preference for social and interpersonal activities"
            }
        ]
        
        result = self.validator.validate_preference_data(data)
        
        assert result.is_valid
        assert result.error_count == 0
        assert result.empty_vs_invalid == "valid"
        assert result.data_quality_score > 0.7
    
    def test_validate_preference_data_empty_data(self):
        """Test validation with empty preference data"""
        data = []
        
        result = self.validator.validate_preference_data(data)
        
        assert result.empty_vs_invalid == "empty"
        assert result.warning_count >= 1
        assert any("No preference data found" in issue.message for issue in result.issues)
    
    def test_validate_preference_data_insufficient_rows(self):
        """Test validation with fewer than 3 preferences"""
        data = [
            {
                "preference_name": "Visual Arts",
                "question_count": 15,
                "response_rate": 85.0,
                "rank": 1,
                "description": "Strong preference for visual activities"
            }
        ]
        
        result = self.validator.validate_preference_data(data)
        
        assert result.warning_count >= 1
        assert any("Expected 3 top preferences" in issue.message for issue in result.issues)
    
    def test_validate_preference_data_missing_fields(self):
        """Test validation with missing required fields"""
        data = [
            {
                "preference_name": "Visual Arts",
                "rank": 1
                # Missing question_count, response_rate, description
            }
        ]
        
        result = self.validator.validate_preference_data(data)
        
        assert not result.is_valid
        assert result.error_count >= 3
        missing_fields = [issue.field_name for issue in result.issues if "Missing required field" in issue.message]
        assert "question_count" in missing_fields
        assert "response_rate" in missing_fields
        assert "description" in missing_fields
    
    def test_validate_preference_data_empty_values(self):
        """Test validation with empty string values"""
        data = [
            {
                "preference_name": "",  # Empty string
                "question_count": 15,
                "response_rate": 85.0,
                "rank": 1,
                "description": "   "  # Whitespace only
            }
        ]
        
        result = self.validator.validate_preference_data(data)
        
        assert result.warning_count >= 2
        empty_warnings = [issue for issue in result.issues if "Empty value" in issue.message]
        assert len(empty_warnings) >= 2
    
    def test_validate_preference_data_invalid_ranks(self):
        """Test validation with invalid rank values"""
        data = [
            {
                "preference_name": "Test Preference",
                "question_count": 10,
                "response_rate": 80.0,
                "rank": 0,  # Invalid rank
                "description": "Test description"
            },
            {
                "preference_name": "Another Preference",
                "question_count": 8,
                "response_rate": 75.0,
                "rank": 5,  # Invalid rank (> 3)
                "description": "Another test description"
            }
        ]
        
        result = self.validator.validate_preference_data(data)
        
        assert not result.is_valid
        assert result.error_count >= 2
        rank_errors = [issue for issue in result.issues if issue.field_name == "rank" and issue.severity == ValidationSeverity.ERROR]
        assert len(rank_errors) == 2
    
    def test_validate_preference_data_invalid_response_rates(self):
        """Test validation with invalid response rates"""
        data = [
            {
                "preference_name": "Test Preference",
                "question_count": 10,
                "response_rate": -5.0,  # Negative
                "rank": 1,
                "description": "Test description"
            },
            {
                "preference_name": "Another Preference",
                "question_count": 8,
                "response_rate": 150.0,  # > 100%
                "rank": 2,
                "description": "Another test description"
            }
        ]
        
        result = self.validator.validate_preference_data(data)
        
        assert not result.is_valid
        assert result.error_count >= 2
        rate_errors = [issue for issue in result.issues if "response_rate" in issue.field_name and issue.severity == ValidationSeverity.ERROR]
        assert len(rate_errors) >= 2
    
    def test_validate_preference_data_short_descriptions(self):
        """Test validation with too-short descriptions"""
        data = [
            {
                "preference_name": "A",  # Too short
                "question_count": 10,
                "response_rate": 80.0,
                "rank": 1,
                "description": "Short"  # Too short
            }
        ]
        
        result = self.validator.validate_preference_data(data)
        
        assert result.warning_count >= 2
        short_warnings = [issue for issue in result.issues if "too short" in issue.message]
        assert len(short_warnings) >= 2
    
    def test_validate_preference_data_missing_ranks(self):
        """Test validation with missing expected ranks"""
        data = [
            {
                "preference_name": "First Preference",
                "question_count": 10,
                "response_rate": 80.0,
                "rank": 1,
                "description": "First preference description"
            },
            {
                "preference_name": "Third Preference",
                "question_count": 8,
                "response_rate": 70.0,
                "rank": 3,  # Missing rank 2
                "description": "Third preference description"
            },
            {
                "preference_name": "Fourth Preference",
                "question_count": 6,
                "response_rate": 60.0,
                "rank": 1,  # Duplicate rank 1
                "description": "Fourth preference description"
            }
        ]
        
        result = self.validator.validate_preference_data(data)
        
        assert result.warning_count >= 1
        assert any("Missing preference ranks" in issue.message for issue in result.issues)
    
    # ==================== Preference Jobs Tests ====================
    
    def test_validate_preference_jobs_valid_data(self):
        """Test validation with valid preference jobs data"""
        data = [
            {
                "preference_name": "Visual Arts",
                "preference_type": "rimg1",
                "jo_name": "Graphic Designer",
                "jo_outline": "Create visual concepts and designs for various media",
                "jo_mainbusiness": "Design graphics for websites, advertisements, and print materials",
                "majors": "Art, Design, Visual Communications"
            },
            {
                "preference_name": "Technical Skills",
                "preference_type": "rimg2",
                "jo_name": "Software Engineer",
                "jo_outline": "Develop and maintain software applications",
                "jo_mainbusiness": "Write code, debug programs, and collaborate with development teams",
                "majors": "Computer Science, Software Engineering"
            },
            {
                "preference_name": "Social Interaction",
                "preference_type": "rimg3",
                "jo_name": "Human Resources Manager",
                "jo_outline": "Manage employee relations and organizational development",
                "jo_mainbusiness": "Recruit staff, handle employee issues, and develop HR policies",
                "majors": "Human Resources, Psychology, Business Administration"
            }
        ]
        
        result = self.validator.validate_preference_jobs(data)
        
        assert result.is_valid
        assert result.error_count == 0
        assert result.empty_vs_invalid == "valid"
        assert result.data_quality_score > 0.7
    
    def test_validate_preference_jobs_empty_data(self):
        """Test validation with empty jobs data"""
        data = []
        
        result = self.validator.validate_preference_jobs(data)
        
        assert result.empty_vs_invalid == "empty"
        assert result.warning_count >= 1
        assert any("No preference jobs data found" in issue.message for issue in result.issues)
    
    def test_validate_preference_jobs_missing_fields(self):
        """Test validation with missing required fields"""
        data = [
            {
                "preference_name": "Visual Arts",
                "preference_type": "rimg1",
                "jo_name": "Graphic Designer"
                # Missing jo_outline, jo_mainbusiness, majors
            }
        ]
        
        result = self.validator.validate_preference_jobs(data)
        
        assert not result.is_valid
        assert result.error_count >= 3
        missing_fields = [issue.field_name for issue in result.issues if "Missing required field" in issue.message]
        assert "jo_outline" in missing_fields
        assert "jo_mainbusiness" in missing_fields
        assert "majors" in missing_fields
    
    def test_validate_preference_jobs_invalid_preference_types(self):
        """Test validation with invalid preference types"""
        data = [
            {
                "preference_name": "Test Preference",
                "preference_type": "invalid_type",  # Invalid
                "jo_name": "Test Job",
                "jo_outline": "Test job outline description",
                "jo_mainbusiness": "Test main business description",
                "majors": "Test Major"
            }
        ]
        
        result = self.validator.validate_preference_jobs(data)
        
        assert not result.is_valid
        assert result.error_count >= 1
        type_errors = [issue for issue in result.issues if issue.field_name == "preference_type" and issue.severity == ValidationSeverity.ERROR]
        assert len(type_errors) >= 1
    
    def test_validate_preference_jobs_missing_preference_types(self):
        """Test validation with missing preference types"""
        data = [
            {
                "preference_name": "Visual Arts",
                "preference_type": "rimg1",  # Only rimg1, missing rimg2 and rimg3
                "jo_name": "Graphic Designer",
                "jo_outline": "Create visual concepts and designs",
                "jo_mainbusiness": "Design graphics for various media",
                "majors": "Art, Design"
            }
        ]
        
        result = self.validator.validate_preference_jobs(data)
        
        assert result.warning_count >= 1
        assert any("Missing preference types" in issue.message for issue in result.issues)
    
    def test_validate_preference_jobs_short_descriptions(self):
        """Test validation with too-short descriptions"""
        data = [
            {
                "preference_name": "Test",
                "preference_type": "rimg1",
                "jo_name": "A",  # Too short
                "jo_outline": "Short",  # Too short
                "jo_mainbusiness": "Brief",  # Too short
                "majors": "X"  # Too short
            }
        ]
        
        result = self.validator.validate_preference_jobs(data)
        
        assert result.warning_count >= 4
        short_warnings = [issue for issue in result.issues if "too short" in issue.message]
        assert len(short_warnings) >= 4
    
    def test_validate_preference_jobs_low_job_distribution(self):
        """Test validation with low job count per preference type"""
        data = [
            {
                "preference_name": "Visual Arts",
                "preference_type": "rimg1",
                "jo_name": "Graphic Designer",
                "jo_outline": "Create visual concepts and designs for various media",
                "jo_mainbusiness": "Design graphics for websites and advertisements",
                "majors": "Art, Design"
            },
            {
                "preference_name": "Technical Skills",
                "preference_type": "rimg2",
                "jo_name": "Software Engineer",
                "jo_outline": "Develop and maintain software applications",
                "jo_mainbusiness": "Write code and debug programs for clients",
                "majors": "Computer Science"
            }
            # Only 1 job per type, should trigger low job count warning
        ]
        
        result = self.validator.validate_preference_jobs(data)
        
        assert result.warning_count >= 2
        job_count_warnings = [issue for issue in result.issues if "Low job count" in issue.message]
        assert len(job_count_warnings) >= 2
    
    def test_validate_preference_jobs_majors_list_format(self):
        """Test validation with majors as list format"""
        data = [
            {
                "preference_name": "Visual Arts",
                "preference_type": "rimg1",
                "jo_name": "Graphic Designer",
                "jo_outline": "Create visual concepts and designs for various media",
                "jo_mainbusiness": "Design graphics for websites and advertisements",
                "majors": ["Art", "Design", "Visual Communications"]  # List format
            },
            {
                "preference_name": "Technical Skills",
                "preference_type": "rimg2",
                "jo_name": "Software Engineer",
                "jo_outline": "Develop and maintain software applications",
                "jo_mainbusiness": "Write code and debug programs for clients",
                "majors": []  # Empty list
            }
        ]
        
        result = self.validator.validate_preference_jobs(data)
        
        assert result.warning_count >= 1
        empty_list_warnings = [issue for issue in result.issues if "Empty majors list" in issue.message]
        assert len(empty_list_warnings) >= 1
    
    # ==================== Comprehensive Validation Tests ====================
    
    def test_validate_all_preference_queries_complete(self):
        """Test validation of all preference queries with complete data"""
        image_stats = [{
            "total_image_count": 100,
            "response_count": 85,
            "response_rate": 85.0
        }]
        
        preference_data = [
            {
                "preference_name": "Visual Arts",
                "question_count": 15,
                "response_rate": 85.0,
                "rank": 1,
                "description": "Strong preference for visual activities"
            }
        ]
        
        preference_jobs = [
            {
                "preference_name": "Visual Arts",
                "preference_type": "rimg1",
                "jo_name": "Graphic Designer",
                "jo_outline": "Create visual concepts and designs",
                "jo_mainbusiness": "Design graphics for various media",
                "majors": "Art, Design"
            }
        ]
        
        results = self.validator.validate_all_preference_queries(
            image_stats_data=image_stats,
            preference_data=preference_data,
            preference_jobs_data=preference_jobs
        )
        
        assert len(results) == 3
        assert "imagePreferenceStatsQuery" in results
        assert "preferenceDataQuery" in results
        assert "preferenceJobsQuery" in results
        
        # All should be valid (though may have warnings)
        for result in results.values():
            assert isinstance(result, ValidationResult)
    
    def test_validate_all_preference_queries_partial(self):
        """Test validation with only some queries provided"""
        image_stats = [{
            "total_image_count": 100,
            "response_count": 85,
            "response_rate": 85.0
        }]
        
        results = self.validator.validate_all_preference_queries(
            image_stats_data=image_stats,
            preference_data=None,  # Not provided
            preference_jobs_data=None  # Not provided
        )
        
        assert len(results) == 1
        assert "imagePreferenceStatsQuery" in results
        assert "preferenceDataQuery" not in results
        assert "preferenceJobsQuery" not in results
    
    def test_generate_validation_report_comprehensive(self):
        """Test generation of comprehensive validation report"""
        # Create validation results with various issues
        results = {
            "imagePreferenceStatsQuery": ValidationResult(
                is_valid=True,
                error_count=0,
                warning_count=1,
                data_quality_score=0.8,
                empty_vs_invalid="valid"
            ),
            "preferenceDataQuery": ValidationResult(
                is_valid=False,
                error_count=0,  # Start with 0, will be incremented by add_issue
                warning_count=1,
                data_quality_score=0.4,
                empty_vs_invalid="invalid"
            ),
            "preferenceJobsQuery": ValidationResult(
                is_valid=True,
                error_count=0,
                warning_count=0,
                data_quality_score=0.9,
                empty_vs_invalid="valid"
            )
        }
        
        # Add some sample issues to match the expected error count
        results["preferenceDataQuery"].add_issue(ValidationIssue(
            field_name="rank",
            issue_type="invalid_range",
            severity=ValidationSeverity.ERROR,
            message="Invalid rank value",
            row_index=0
        ))
        results["preferenceDataQuery"].add_issue(ValidationIssue(
            field_name="response_rate",
            issue_type="out_of_range",
            severity=ValidationSeverity.ERROR,
            message="Invalid response rate",
            row_index=1
        ))
        
        report = self.validator.generate_validation_report(results)
        
        assert "overall_valid" in report
        assert not report["overall_valid"]  # Should be False due to errors
        
        assert "summary" in report
        summary = report["summary"]
        assert summary["total_queries_validated"] == 3
        assert summary["total_errors"] == 2
        assert summary["total_warnings"] == 2
        
        assert "query_results" in report
        assert len(report["query_results"]) == 3
        
        assert "issues" in report
        assert len(report["issues"]) >= 1
        
        assert "recommendations" in report
        assert len(report["recommendations"]) > 0
        
        assert "timestamp" in report
    
    def test_generate_validation_report_all_valid(self):
        """Test validation report generation with all valid results"""
        results = {
            "imagePreferenceStatsQuery": ValidationResult(
                is_valid=True,
                error_count=0,
                warning_count=0,
                data_quality_score=0.9,
                empty_vs_invalid="valid"
            ),
            "preferenceDataQuery": ValidationResult(
                is_valid=True,
                error_count=0,
                warning_count=0,
                data_quality_score=0.8,
                empty_vs_invalid="valid"
            )
        }
        
        report = self.validator.generate_validation_report(results)
        
        assert report["overall_valid"]
        assert report["summary"]["total_errors"] == 0
        assert report["summary"]["average_quality_score"] > 0.8
    
    # ==================== Edge Cases and Error Handling ====================
    
    def test_validation_with_none_data(self):
        """Test validation behavior with None data"""
        result = self.validator.validate_image_preference_stats(None)
        
        assert result.empty_vs_invalid == "empty"
        assert result.warning_count >= 1
    
    def test_validation_with_malformed_data(self):
        """Test validation with malformed data structures"""
        # Test with non-dict items in list
        data = ["not_a_dict", {"valid": "dict"}]
        
        # Should handle gracefully without crashing
        try:
            result = self.validator.validate_preference_data(data)
            # Should detect issues with malformed data
            assert result.error_count > 0 or result.warning_count > 0
        except Exception as e:
            # If it raises an exception, it should be a controlled one
            assert "validation" in str(e).lower() or "invalid" in str(e).lower()
    
    def test_validation_issue_creation(self):
        """Test ValidationIssue creation and methods"""
        issue = ValidationIssue(
            field_name="test_field",
            issue_type="test_type",
            severity=ValidationSeverity.ERROR,
            message="Test message",
            expected_value="expected",
            actual_value="actual",
            row_index=5
        )
        
        assert issue.field_name == "test_field"
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.row_index == 5
    
    def test_validation_result_methods(self):
        """Test ValidationResult methods"""
        result = ValidationResult(is_valid=True)
        
        # Test adding issues
        error_issue = ValidationIssue(
            field_name="test",
            issue_type="error",
            severity=ValidationSeverity.ERROR,
            message="Error message"
        )
        
        warning_issue = ValidationIssue(
            field_name="test",
            issue_type="warning",
            severity=ValidationSeverity.WARNING,
            message="Warning message"
        )
        
        result.add_issue(error_issue)
        result.add_issue(warning_issue)
        
        assert not result.is_valid  # Should become False after adding error
        assert result.error_count == 1
        assert result.warning_count == 1
        
        # Test getting issues by severity
        errors = result.get_issues_by_severity(ValidationSeverity.ERROR)
        warnings = result.get_issues_by_severity(ValidationSeverity.WARNING)
        
        assert len(errors) == 1
        assert len(warnings) == 1
        assert errors[0] == error_issue
        assert warnings[0] == warning_issue
        
        # Test summary
        summary = result.get_summary()
        assert "Invalid" in summary
        assert "1 errors" in summary
        assert "1 warnings" in summary


# ==================== Integration Tests ====================

class TestPreferenceDataValidatorIntegration:
    """Integration tests for PreferenceDataValidator with realistic data"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = PreferenceDataValidator()
    
    def test_realistic_preference_data_scenario(self):
        """Test with realistic preference data scenario"""
        # Simulate realistic data that might come from actual queries
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
        results = self.validator.validate_all_preference_queries(
            image_stats_data=image_stats,
            preference_data=preference_data,
            preference_jobs_data=preference_jobs
        )
        
        # Generate comprehensive report
        report = self.validator.generate_validation_report(results)
        
        # All should be valid with good quality scores
        assert report["overall_valid"]
        assert report["summary"]["total_errors"] == 0
        assert report["summary"]["average_quality_score"] > 0.7
        
        # Check individual query results
        for query_name, query_result in report["query_results"].items():
            assert query_result["valid"]
            assert query_result["quality_score"] > 0.7
            assert query_result["data_status"] == "valid"
    
    def test_problematic_data_scenario(self):
        """Test with problematic data that should trigger various warnings and errors"""
        # Simulate problematic data
        image_stats = [{
            "total_image_count": 50,
            "response_count": 15,  # Low response count
            "response_rate": 25.0  # Low response rate
        }]
        
        preference_data = [
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
        
        preference_jobs = [
            {
                "preference_name": "Test",
                "preference_type": "invalid_type",  # Invalid type
                "jo_name": "X",  # Too short
                "jo_outline": "Short outline",  # Too short
                "jo_mainbusiness": "Brief",  # Too short
                "majors": ""  # Empty
            }
        ]
        
        # Validate all queries
        results = self.validator.validate_all_preference_queries(
            image_stats_data=image_stats,
            preference_data=preference_data,
            preference_jobs_data=preference_jobs
        )
        
        # Generate comprehensive report
        report = self.validator.generate_validation_report(results)
        
        # Should have multiple issues
        assert not report["overall_valid"]
        assert report["summary"]["total_errors"] > 0
        assert report["summary"]["total_warnings"] > 0
        assert len(report["recommendations"]) > 0
        
        # Should have specific recommendations for critical issues
        recommendations = report["recommendations"]
        assert any("CRITICAL" in rec for rec in recommendations)
        assert any("validation errors" in rec for rec in recommendations)


if __name__ == "__main__":
    pytest.main([__file__])