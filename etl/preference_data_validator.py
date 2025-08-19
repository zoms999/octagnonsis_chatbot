"""
Preference Data Validation Service

This module provides comprehensive validation for preference query results,
including validation rules for image preference statistics, preference data structure,
and preference jobs data.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    field_name: str
    issue_type: str
    severity: ValidationSeverity
    message: str
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    row_index: Optional[int] = None


@dataclass
class ValidationResult:
    """Result of data validation with detailed error reporting"""
    is_valid: bool
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    data_quality_score: float = 0.0
    empty_vs_invalid: str = "unknown"  # "empty", "invalid", "valid"
    validation_summary: str = ""
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue and update counters"""
        self.issues.append(issue)
        
        if issue.severity == ValidationSeverity.ERROR:
            self.error_count += 1
            self.is_valid = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warning_count += 1
        elif issue.severity == ValidationSeverity.INFO:
            self.info_count += 1
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get all issues of a specific severity"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_summary(self) -> str:
        """Get a human-readable summary of validation results"""
        if self.is_valid and self.error_count == 0:
            if self.warning_count > 0:
                return f"Valid with {self.warning_count} warnings"
            else:
                return "Valid"
        else:
            return f"Invalid: {self.error_count} errors, {self.warning_count} warnings"


class PreferenceDataValidator:
    """
    Comprehensive validator for preference query results with detailed validation rules
    """
    
    def __init__(self):
        # Validation thresholds
        self.min_response_rate = 30.0  # Minimum acceptable response rate percentage
        self.min_data_quality_score = 0.3  # Minimum acceptable data quality score
        self.max_preference_rank = 3  # Maximum valid preference rank
        self.expected_preference_types = {"rimg1", "rimg2", "rimg3"}
        
    def validate_image_preference_stats(self, data: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate image preference statistics query results
        
        Expected structure:
        - Single row with total_image_count, response_count, response_rate
        - Valid ranges and relationships between fields
        """
        result = ValidationResult(is_valid=True)
        
        # Check if data exists
        if not data:
            result.empty_vs_invalid = "empty"
            result.add_issue(ValidationIssue(
                field_name="data",
                issue_type="missing_data",
                severity=ValidationSeverity.WARNING,
                message="No image preference statistics data found"
            ))
            result.validation_summary = "Empty result set"
            return result
        
        # Check for exactly one row
        if len(data) != 1:
            result.empty_vs_invalid = "invalid"
            result.add_issue(ValidationIssue(
                field_name="row_count",
                issue_type="incorrect_count",
                severity=ValidationSeverity.ERROR,
                message=f"Expected exactly 1 row, got {len(data)}",
                expected_value=1,
                actual_value=len(data)
            ))
        
        if len(data) == 0:
            result.validation_summary = "No data rows"
            return result
        
        row = data[0]
        result.empty_vs_invalid = "valid"
        
        # Required fields validation
        required_fields = ["total_image_count", "response_count", "response_rate"]
        for field in required_fields:
            if field not in row:
                result.add_issue(ValidationIssue(
                    field_name=field,
                    issue_type="missing_field",
                    severity=ValidationSeverity.ERROR,
                    message=f"Required field '{field}' is missing"
                ))
            elif row[field] is None:
                result.add_issue(ValidationIssue(
                    field_name=field,
                    issue_type="null_value",
                    severity=ValidationSeverity.WARNING,
                    message=f"Field '{field}' has null value"
                ))
        
        # Data type and range validation
        total_count = row.get("total_image_count")
        response_count = row.get("response_count")
        response_rate = row.get("response_rate")
        
        # Validate total_image_count
        if total_count is not None:
            if not isinstance(total_count, (int, float)) or total_count < 0:
                result.add_issue(ValidationIssue(
                    field_name="total_image_count",
                    issue_type="invalid_value",
                    severity=ValidationSeverity.ERROR,
                    message="Total image count must be a non-negative number",
                    actual_value=total_count
                ))
            elif total_count == 0:
                result.add_issue(ValidationIssue(
                    field_name="total_image_count",
                    issue_type="zero_value",
                    severity=ValidationSeverity.WARNING,
                    message="Total image count is zero"
                ))
        
        # Validate response_count
        if response_count is not None:
            if not isinstance(response_count, (int, float)) or response_count < 0:
                result.add_issue(ValidationIssue(
                    field_name="response_count",
                    issue_type="invalid_value",
                    severity=ValidationSeverity.ERROR,
                    message="Response count must be a non-negative number",
                    actual_value=response_count
                ))
        
        # Validate response_rate
        if response_rate is not None:
            if not isinstance(response_rate, (int, float)):
                result.add_issue(ValidationIssue(
                    field_name="response_rate",
                    issue_type="invalid_type",
                    severity=ValidationSeverity.ERROR,
                    message="Response rate must be a number",
                    actual_value=type(response_rate).__name__
                ))
            elif not 0 <= response_rate <= 100:
                result.add_issue(ValidationIssue(
                    field_name="response_rate",
                    issue_type="out_of_range",
                    severity=ValidationSeverity.ERROR,
                    message=f"Response rate {response_rate} outside valid range 0-100",
                    expected_value="0-100",
                    actual_value=response_rate
                ))
            elif response_rate < self.min_response_rate:
                result.add_issue(ValidationIssue(
                    field_name="response_rate",
                    issue_type="low_response_rate",
                    severity=ValidationSeverity.WARNING,
                    message=f"Low response rate: {response_rate}% (threshold: {self.min_response_rate}%)",
                    expected_value=f">= {self.min_response_rate}%",
                    actual_value=f"{response_rate}%"
                ))
        
        # Cross-field validation
        if (total_count is not None and response_count is not None and 
            isinstance(total_count, (int, float)) and isinstance(response_count, (int, float))):
            
            if response_count > total_count:
                result.add_issue(ValidationIssue(
                    field_name="response_count",
                    issue_type="logical_error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Response count ({response_count}) exceeds total count ({total_count})",
                    expected_value=f"<= {total_count}",
                    actual_value=response_count
                ))
            
            # Validate calculated response rate
            if total_count > 0 and response_rate is not None:
                calculated_rate = (response_count / total_count) * 100
                rate_diff = abs(calculated_rate - response_rate)
                
                if rate_diff > 1.0:  # Allow 1% tolerance for rounding
                    result.add_issue(ValidationIssue(
                        field_name="response_rate",
                        issue_type="calculation_mismatch",
                        severity=ValidationSeverity.WARNING,
                        message=f"Response rate {response_rate}% doesn't match calculated rate {calculated_rate:.1f}%",
                        expected_value=f"{calculated_rate:.1f}%",
                        actual_value=f"{response_rate}%"
                    ))
        
        # Calculate data quality score
        result.data_quality_score = self._calculate_image_stats_quality_score(row, result)
        result.validation_summary = result.get_summary()
        
        return result
    
    def validate_preference_data(self, data: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate preference data query results
        
        Expected structure:
        - Multiple rows with preference_name, question_count, response_rate, rank, description
        - Valid ranks (1-3), response rates (0-100%), non-empty names and descriptions
        """
        result = ValidationResult(is_valid=True)
        
        # Check if data exists
        if not data:
            result.empty_vs_invalid = "empty"
            result.add_issue(ValidationIssue(
                field_name="data",
                issue_type="missing_data",
                severity=ValidationSeverity.WARNING,
                message="No preference data found - may indicate missing test results"
            ))
            result.validation_summary = "Empty result set"
            return result
        
        result.empty_vs_invalid = "valid"
        
        # Expected to have top 3 preferences
        if len(data) < 3:
            result.add_issue(ValidationIssue(
                field_name="row_count",
                issue_type="insufficient_data",
                severity=ValidationSeverity.WARNING,
                message=f"Expected 3 top preferences, got {len(data)}",
                expected_value=3,
                actual_value=len(data)
            ))
        
        required_fields = ["preference_name", "question_count", "response_rate", "rank", "description"]
        ranks_found = set()
        
        # Validate each preference row
        for i, row in enumerate(data):
            row_prefix = f"Row {i+1}"
            
            # Check if row is a dictionary
            if not isinstance(row, dict):
                result.add_issue(ValidationIssue(
                    field_name="row_structure",
                    issue_type="invalid_type",
                    severity=ValidationSeverity.ERROR,
                    message=f"{row_prefix}: Row must be a dictionary, got {type(row).__name__}",
                    row_index=i
                ))
                continue
            
            # Check required fields
            for field in required_fields:
                if field not in row:
                    result.add_issue(ValidationIssue(
                        field_name=field,
                        issue_type="missing_field",
                        severity=ValidationSeverity.ERROR,
                        message=f"{row_prefix}: Missing required field '{field}'",
                        row_index=i
                    ))
                elif row[field] is None or (isinstance(row[field], str) and row[field].strip() == ""):
                    result.add_issue(ValidationIssue(
                        field_name=field,
                        issue_type="empty_value",
                        severity=ValidationSeverity.WARNING,
                        message=f"{row_prefix}: Empty value in field '{field}'",
                        row_index=i
                    ))
            
            # Validate preference_name
            preference_name = row.get("preference_name")
            if preference_name and isinstance(preference_name, str):
                if len(preference_name.strip()) < 2:
                    result.add_issue(ValidationIssue(
                        field_name="preference_name",
                        issue_type="too_short",
                        severity=ValidationSeverity.WARNING,
                        message=f"{row_prefix}: Preference name too short: '{preference_name}'",
                        row_index=i
                    ))
            
            # Validate rank
            rank = row.get("rank")
            if rank is not None:
                if not isinstance(rank, int) or rank < 1 or rank > self.max_preference_rank:
                    result.add_issue(ValidationIssue(
                        field_name="rank",
                        issue_type="invalid_range",
                        severity=ValidationSeverity.ERROR,
                        message=f"{row_prefix}: Invalid rank {rank}, expected 1-{self.max_preference_rank}",
                        expected_value=f"1-{self.max_preference_rank}",
                        actual_value=rank,
                        row_index=i
                    ))
                else:
                    ranks_found.add(rank)
            
            # Validate response_rate
            response_rate = row.get("response_rate")
            if response_rate is not None:
                if not isinstance(response_rate, (int, float)):
                    result.add_issue(ValidationIssue(
                        field_name="response_rate",
                        issue_type="invalid_type",
                        severity=ValidationSeverity.ERROR,
                        message=f"{row_prefix}: Response rate must be a number",
                        actual_value=type(response_rate).__name__,
                        row_index=i
                    ))
                elif not 0 <= response_rate <= 100:
                    result.add_issue(ValidationIssue(
                        field_name="response_rate",
                        issue_type="out_of_range",
                        severity=ValidationSeverity.ERROR,
                        message=f"{row_prefix}: Invalid response rate {response_rate}",
                        expected_value="0-100",
                        actual_value=response_rate,
                        row_index=i
                    ))
                elif response_rate < self.min_response_rate:
                    result.add_issue(ValidationIssue(
                        field_name="response_rate",
                        issue_type="low_response_rate",
                        severity=ValidationSeverity.WARNING,
                        message=f"{row_prefix}: Low response rate {response_rate}%",
                        expected_value=f">= {self.min_response_rate}%",
                        actual_value=f"{response_rate}%",
                        row_index=i
                    ))
            
            # Validate question_count
            question_count = row.get("question_count")
            if question_count is not None:
                if not isinstance(question_count, int) or question_count < 0:
                    result.add_issue(ValidationIssue(
                        field_name="question_count",
                        issue_type="invalid_value",
                        severity=ValidationSeverity.ERROR,
                        message=f"{row_prefix}: Invalid question count {question_count}",
                        expected_value=">= 0",
                        actual_value=question_count,
                        row_index=i
                    ))
                elif question_count == 0:
                    result.add_issue(ValidationIssue(
                        field_name="question_count",
                        issue_type="zero_value",
                        severity=ValidationSeverity.WARNING,
                        message=f"{row_prefix}: Zero questions for preference",
                        row_index=i
                    ))
            
            # Validate description
            description = row.get("description")
            if description and isinstance(description, str):
                if len(description.strip()) < 10:
                    result.add_issue(ValidationIssue(
                        field_name="description",
                        issue_type="too_short",
                        severity=ValidationSeverity.WARNING,
                        message=f"{row_prefix}: Description too short (< 10 characters)",
                        row_index=i
                    ))
        
        # Check for missing ranks in top 3
        expected_ranks = {1, 2, 3}
        missing_ranks = expected_ranks - ranks_found
        if missing_ranks and len(data) >= 3:
            result.add_issue(ValidationIssue(
                field_name="rank",
                issue_type="missing_ranks",
                severity=ValidationSeverity.WARNING,
                message=f"Missing preference ranks: {sorted(missing_ranks)}",
                expected_value=list(expected_ranks),
                actual_value=list(ranks_found)
            ))
        
        # Calculate data quality score
        result.data_quality_score = self._calculate_preference_data_quality_score(data, result)
        result.validation_summary = result.get_summary()
        
        return result
    
    def validate_preference_jobs(self, data: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate preference jobs query results
        
        Expected structure:
        - Multiple rows with preference_name, preference_type, jo_name, jo_outline, jo_mainbusiness, majors
        - Valid preference types (rimg1, rimg2, rimg3)
        - Non-empty job names and descriptions
        """
        result = ValidationResult(is_valid=True)
        
        # Check if data exists
        if not data:
            result.empty_vs_invalid = "empty"
            result.add_issue(ValidationIssue(
                field_name="data",
                issue_type="missing_data",
                severity=ValidationSeverity.WARNING,
                message="No preference jobs data found - may indicate missing test results"
            ))
            result.validation_summary = "Empty result set"
            return result
        
        result.empty_vs_invalid = "valid"
        
        required_fields = ["preference_name", "preference_type", "jo_name", "jo_outline", "jo_mainbusiness", "majors"]
        found_preference_types = set()
        jobs_per_type = {}
        
        # Validate each job row
        for i, row in enumerate(data):
            row_prefix = f"Row {i+1}"
            
            # Check if row is a dictionary
            if not isinstance(row, dict):
                result.add_issue(ValidationIssue(
                    field_name="row_structure",
                    issue_type="invalid_type",
                    severity=ValidationSeverity.ERROR,
                    message=f"{row_prefix}: Row must be a dictionary, got {type(row).__name__}",
                    row_index=i
                ))
                continue
            
            # Check required fields
            for field in required_fields:
                if field not in row:
                    result.add_issue(ValidationIssue(
                        field_name=field,
                        issue_type="missing_field",
                        severity=ValidationSeverity.ERROR,
                        message=f"{row_prefix}: Missing required field '{field}'",
                        row_index=i
                    ))
                elif row[field] is None or (isinstance(row[field], str) and row[field].strip() == ""):
                    result.add_issue(ValidationIssue(
                        field_name=field,
                        issue_type="empty_value",
                        severity=ValidationSeverity.WARNING,
                        message=f"{row_prefix}: Empty value in field '{field}'",
                        row_index=i
                    ))
            
            # Validate preference_type
            preference_type = row.get("preference_type")
            if preference_type:
                found_preference_types.add(preference_type)
                
                if preference_type not in self.expected_preference_types:
                    result.add_issue(ValidationIssue(
                        field_name="preference_type",
                        issue_type="invalid_value",
                        severity=ValidationSeverity.ERROR,
                        message=f"{row_prefix}: Invalid preference type '{preference_type}'",
                        expected_value=list(self.expected_preference_types),
                        actual_value=preference_type,
                        row_index=i
                    ))
                else:
                    # Count jobs per preference type
                    jobs_per_type[preference_type] = jobs_per_type.get(preference_type, 0) + 1
            
            # Validate job name
            jo_name = row.get("jo_name")
            if jo_name and isinstance(jo_name, str):
                if len(jo_name.strip()) < 2:
                    result.add_issue(ValidationIssue(
                        field_name="jo_name",
                        issue_type="too_short",
                        severity=ValidationSeverity.WARNING,
                        message=f"{row_prefix}: Job name too short: '{jo_name}'",
                        row_index=i
                    ))
            
            # Validate job outline
            jo_outline = row.get("jo_outline")
            if jo_outline and isinstance(jo_outline, str):
                if len(jo_outline.strip()) < 10:
                    result.add_issue(ValidationIssue(
                        field_name="jo_outline",
                        issue_type="too_short",
                        severity=ValidationSeverity.WARNING,
                        message=f"{row_prefix}: Job outline too short (< 10 characters)",
                        row_index=i
                    ))
            
            # Validate main business
            jo_mainbusiness = row.get("jo_mainbusiness")
            if jo_mainbusiness and isinstance(jo_mainbusiness, str):
                if len(jo_mainbusiness.strip()) < 10:
                    result.add_issue(ValidationIssue(
                        field_name="jo_mainbusiness",
                        issue_type="too_short",
                        severity=ValidationSeverity.WARNING,
                        message=f"{row_prefix}: Main business description too short (< 10 characters)",
                        row_index=i
                    ))
            
            # Validate majors (can be string or list)
            majors = row.get("majors")
            if majors is not None:
                if isinstance(majors, str):
                    if len(majors.strip()) < 2:
                        result.add_issue(ValidationIssue(
                            field_name="majors",
                            issue_type="too_short",
                            severity=ValidationSeverity.WARNING,
                            message=f"{row_prefix}: Majors field too short",
                            row_index=i
                        ))
                elif isinstance(majors, list):
                    if len(majors) == 0:
                        result.add_issue(ValidationIssue(
                            field_name="majors",
                            issue_type="empty_list",
                            severity=ValidationSeverity.WARNING,
                            message=f"{row_prefix}: Empty majors list",
                            row_index=i
                        ))
        
        # Check for missing preference types
        missing_types = self.expected_preference_types - found_preference_types
        if missing_types:
            result.add_issue(ValidationIssue(
                field_name="preference_type",
                issue_type="missing_types",
                severity=ValidationSeverity.WARNING,
                message=f"Missing preference types: {', '.join(sorted(missing_types))}",
                expected_value=list(self.expected_preference_types),
                actual_value=list(found_preference_types)
            ))
        
        # Check job distribution per preference type
        for pref_type, job_count in jobs_per_type.items():
            if job_count < 3:
                result.add_issue(ValidationIssue(
                    field_name="job_distribution",
                    issue_type="low_job_count",
                    severity=ValidationSeverity.WARNING,
                    message=f"Low job count for {pref_type}: {job_count} jobs",
                    expected_value=">= 3",
                    actual_value=job_count
                ))
        
        # Calculate data quality score
        result.data_quality_score = self._calculate_preference_jobs_quality_score(data, result)
        result.validation_summary = result.get_summary()
        
        return result
    
    def validate_all_preference_queries(
        self, 
        image_stats_data: Optional[List[Dict[str, Any]]] = None,
        preference_data: Optional[List[Dict[str, Any]]] = None,
        preference_jobs_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, ValidationResult]:
        """
        Validate all preference query results and return comprehensive report
        
        Args:
            image_stats_data: Results from imagePreferenceStatsQuery
            preference_data: Results from preferenceDataQuery  
            preference_jobs_data: Results from preferenceJobsQuery
            
        Returns:
            Dictionary mapping query names to their validation results
        """
        results = {}
        
        if image_stats_data is not None:
            results["imagePreferenceStatsQuery"] = self.validate_image_preference_stats(image_stats_data)
        
        if preference_data is not None:
            results["preferenceDataQuery"] = self.validate_preference_data(preference_data)
        
        if preference_jobs_data is not None:
            results["preferenceJobsQuery"] = self.validate_preference_jobs(preference_jobs_data)
        
        return results
    
    def generate_validation_report(self, validation_results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """
        Generate a comprehensive validation report from multiple validation results
        
        Args:
            validation_results: Dictionary of query name to ValidationResult
            
        Returns:
            Comprehensive validation report
        """
        total_errors = sum(result.error_count for result in validation_results.values())
        total_warnings = sum(result.warning_count for result in validation_results.values())
        total_info = sum(result.info_count for result in validation_results.values())
        
        overall_valid = all(result.is_valid for result in validation_results.values())
        
        # Calculate overall quality score
        quality_scores = [result.data_quality_score for result in validation_results.values() 
                         if result.data_quality_score > 0]
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Categorize issues by severity
        all_issues = []
        for query_name, result in validation_results.items():
            for issue in result.issues:
                issue_dict = {
                    "query": query_name,
                    "field": issue.field_name,
                    "type": issue.issue_type,
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "row_index": issue.row_index
                }
                if issue.expected_value is not None:
                    issue_dict["expected"] = issue.expected_value
                if issue.actual_value is not None:
                    issue_dict["actual"] = issue.actual_value
                all_issues.append(issue_dict)
        
        # Generate recommendations
        recommendations = self._generate_validation_recommendations(validation_results)
        
        return {
            "overall_valid": overall_valid,
            "summary": {
                "total_queries_validated": len(validation_results),
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "total_info": total_info,
                "average_quality_score": avg_quality_score
            },
            "query_results": {
                query_name: {
                    "valid": result.is_valid,
                    "errors": result.error_count,
                    "warnings": result.warning_count,
                    "quality_score": result.data_quality_score,
                    "summary": result.validation_summary,
                    "data_status": result.empty_vs_invalid
                }
                for query_name, result in validation_results.items()
            },
            "issues": all_issues,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_image_stats_quality_score(self, row: Dict[str, Any], result: ValidationResult) -> float:
        """Calculate quality score for image preference statistics"""
        score = 1.0
        
        # Deduct for errors
        score -= result.error_count * 0.3
        
        # Deduct for warnings
        score -= result.warning_count * 0.1
        
        # Bonus for good response rate
        response_rate = row.get("response_rate", 0)
        if isinstance(response_rate, (int, float)) and response_rate >= 80:
            score += 0.1
        elif isinstance(response_rate, (int, float)) and response_rate < 30:
            score -= 0.2
        
        # Bonus for reasonable total count
        total_count = row.get("total_image_count", 0)
        if isinstance(total_count, (int, float)) and total_count > 0:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _calculate_preference_data_quality_score(self, data: List[Dict[str, Any]], result: ValidationResult) -> float:
        """Calculate quality score for preference data"""
        if not data:
            return 0.0
        
        score = 1.0
        
        # Deduct for errors and warnings
        score -= result.error_count * 0.2
        score -= result.warning_count * 0.05
        
        # Bonus for having expected number of preferences
        if len(data) >= 3:
            score += 0.1
        
        # Check data completeness
        complete_rows = 0
        for row in data:
            if isinstance(row, dict) and all(row.get(field) for field in ["preference_name", "rank", "description"]):
                complete_rows += 1
        
        completeness_ratio = complete_rows / len(data)
        score *= completeness_ratio
        
        return max(0.0, min(1.0, score))
    
    def _calculate_preference_jobs_quality_score(self, data: List[Dict[str, Any]], result: ValidationResult) -> float:
        """Calculate quality score for preference jobs data"""
        if not data:
            return 0.0
        
        score = 1.0
        
        # Deduct for errors and warnings
        score -= result.error_count * 0.15
        score -= result.warning_count * 0.05
        
        # Check preference type coverage
        found_types = set(row.get("preference_type") for row in data if isinstance(row, dict) and row.get("preference_type"))
        type_coverage = len(found_types & self.expected_preference_types) / len(self.expected_preference_types)
        score *= type_coverage
        
        # Check data completeness
        complete_rows = 0
        for row in data:
            if isinstance(row, dict) and all(row.get(field) for field in ["jo_name", "jo_outline", "preference_type"]):
                complete_rows += 1
        
        completeness_ratio = complete_rows / len(data)
        score *= completeness_ratio
        
        return max(0.0, min(1.0, score))
    
    def _generate_validation_recommendations(self, validation_results: Dict[str, ValidationResult]) -> List[str]:
        """Generate actionable recommendations based on validation results"""
        recommendations = []
        
        # Check for critical issues
        total_errors = sum(result.error_count for result in validation_results.values())
        if total_errors > 0:
            recommendations.append(
                f"CRITICAL: {total_errors} validation errors found. "
                "Review data integrity and query logic before processing."
            )
        
        # Query-specific recommendations
        for query_name, result in validation_results.items():
            if result.empty_vs_invalid == "empty":
                recommendations.append(
                    f"WARNING: {query_name} returns no data. "
                    "Check if user has completed preference assessment."
                )
            elif result.error_count > 0:
                recommendations.append(
                    f"ERROR: {query_name} has {result.error_count} validation errors. "
                    "Review query implementation and data schema."
                )
            elif result.data_quality_score < self.min_data_quality_score:
                recommendations.append(
                    f"QUALITY: {query_name} has low quality score ({result.data_quality_score:.2f}). "
                    "Consider data cleaning or validation rule adjustments."
                )
        
        # Check for missing preference types
        jobs_result = validation_results.get("preferenceJobsQuery")
        if jobs_result:
            missing_type_issues = [
                issue for issue in jobs_result.issues 
                if issue.issue_type == "missing_types"
            ]
            if missing_type_issues:
                recommendations.append(
                    "WARNING: Some preference types missing from jobs data. "
                    "Verify preference assessment completion and data migration."
                )
        
        # Performance recommendations
        total_warnings = sum(result.warning_count for result in validation_results.values())
        if total_warnings > 5:
            recommendations.append(
                f"PERFORMANCE: {total_warnings} validation warnings detected. "
                "Consider implementing data quality monitoring and cleanup processes."
            )
        
        return recommendations

    async def validate_user_preference_data(self, anp_seq: int) -> Dict[str, Any]:
        """
        Validate all preference data for a specific user.
        
        Args:
            anp_seq: User sequence number
            
        Returns:
            Dict containing validation results
        """
        validation_result = {
            "anp_seq": anp_seq,
            "is_valid": True,
            "issues": [],
            "validation_details": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            from etl.legacy_query_executor import LegacyQueryExecutor
            
            query_executor = LegacyQueryExecutor()
            
            # Validate image preference stats
            try:
                stats_data = await query_executor.imagePreferenceStatsQuery(anp_seq)
                stats_validation = await self.validate_image_preference_stats(stats_data)
                validation_result["validation_details"]["imagePreferenceStats"] = stats_validation
                
                if not stats_validation.get("is_valid", False):
                    validation_result["is_valid"] = False
                    validation_result["issues"].extend(stats_validation.get("issues", []))
                    
            except Exception as e:
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"Image preference stats validation failed: {str(e)}")
            
            # Validate preference data
            try:
                pref_data = await query_executor.preferenceDataQuery(anp_seq)
                pref_validation = await self.validate_preference_data(pref_data)
                validation_result["validation_details"]["preferenceData"] = pref_validation
                
                if not pref_validation.get("is_valid", False):
                    validation_result["is_valid"] = False
                    validation_result["issues"].extend(pref_validation.get("issues", []))
                    
            except Exception as e:
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"Preference data validation failed: {str(e)}")
            
            # Validate preference jobs
            try:
                jobs_data = await query_executor.preferenceJobsQuery(anp_seq)
                jobs_validation = await self.validate_preference_jobs(jobs_data)
                validation_result["validation_details"]["preferenceJobs"] = jobs_validation
                
                if not jobs_validation.get("is_valid", False):
                    validation_result["is_valid"] = False
                    validation_result["issues"].extend(jobs_validation.get("issues", []))
                    
            except Exception as e:
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"Preference jobs validation failed: {str(e)}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating user preference data for anp_seq {anp_seq}: {str(e)}")
            validation_result["is_valid"] = False
            validation_result["issues"].append(f"Validation process failed: {str(e)}")
            return validation_result