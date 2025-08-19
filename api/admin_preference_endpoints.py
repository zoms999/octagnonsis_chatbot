"""
Admin API endpoints for preference data management and diagnostics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime

from database.connection import get_async_session
from etl.preference_diagnostics import PreferenceDiagnostics
from etl.preference_data_validator import PreferenceDataValidator
from etl.legacy_query_executor import LegacyQueryExecutor
from database.repositories import DocumentRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/preference", tags=["admin-preference"])

# Response models
class UserPreferenceDiagnostic(BaseModel):
    anp_seq: int
    user_id: Optional[str] = None
    has_preference_documents: bool
    preference_queries_status: Dict[str, Any]
    validation_results: Dict[str, Any]
    document_count: int
    last_processed: Optional[datetime] = None
    issues: List[str]
    recommendations: List[str]

class BulkDiagnosticResult(BaseModel):
    total_users_checked: int
    users_with_issues: int
    users_without_preference_data: int
    common_issues: Dict[str, int]
    affected_users: List[UserPreferenceDiagnostic]

class PreferenceQueryTestResult(BaseModel):
    anp_seq: int
    query_name: str
    success: bool
    execution_time_ms: float
    row_count: int
    error_message: Optional[str] = None
    sample_data: Optional[List[Dict]] = None

class ValidationRepairResult(BaseModel):
    anp_seq: int
    validation_performed: bool
    issues_found: List[str]
    repair_attempted: bool
    repair_successful: bool
    new_documents_created: int
    error_message: Optional[str] = None

@router.get("/diagnose/{anp_seq}", response_model=UserPreferenceDiagnostic)
async def diagnose_user_preference_data(
    anp_seq: int,
    db_session = Depends(get_async_session)
):
    """
    Diagnose preference data issues for a specific user.
    """
    try:
        diagnostics = PreferenceDiagnostics()
        doc_repo = DocumentRepository(db_session)
        
        # Run comprehensive diagnostic
        diagnostic_result = await diagnostics.diagnose_user_preference_data(anp_seq)
        
        # Get document count
        documents = await doc_repo.get_documents_by_anp_seq(anp_seq)
        preference_docs = [doc for doc in documents if doc.document_type == "PREFERENCE_ANALYSIS"]
        
        # Get last processed time
        last_processed = None
        if preference_docs:
            last_processed = max(doc.created_at for doc in preference_docs)
        
        return UserPreferenceDiagnostic(
            anp_seq=anp_seq,
            has_preference_documents=len(preference_docs) > 0,
            preference_queries_status=diagnostic_result.get("query_status", {}),
            validation_results=diagnostic_result.get("validation_results", {}),
            document_count=len(preference_docs),
            last_processed=last_processed,
            issues=diagnostic_result.get("issues", []),
            recommendations=diagnostic_result.get("recommendations", [])
        )
        
    except Exception as e:
        logger.error(f"Error diagnosing preference data for anp_seq {anp_seq}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Diagnostic failed: {str(e)}")

@router.get("/bulk-diagnose", response_model=BulkDiagnosticResult)
async def bulk_diagnose_preference_issues(
    limit: int = Query(100, description="Maximum number of users to check"),
    skip: int = Query(0, description="Number of users to skip"),
    only_issues: bool = Query(False, description="Only return users with issues"),
    db_session = Depends(get_async_session)
):
    """
    Perform bulk diagnostic to identify users with preference data problems.
    """
    try:
        diagnostics = PreferenceDiagnostics()
        doc_repo = DocumentRepository(db_session)
        
        # Get list of users to check
        all_users = await doc_repo.get_unique_anp_seqs(limit=limit + skip)
        users_to_check = all_users[skip:skip + limit]
        
        affected_users = []
        users_with_issues = 0
        users_without_preference_data = 0
        common_issues = {}
        
        for anp_seq in users_to_check:
            try:
                # Run diagnostic for each user
                diagnostic_result = await diagnostics.diagnose_user_preference_data(anp_seq)
                
                # Get document info
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
                
                # Add to results if has issues or if not filtering
                if not only_issues or has_issues or not has_preference_data:
                    last_processed = None
                    if preference_docs:
                        last_processed = max(doc.created_at for doc in preference_docs)
                    
                    affected_users.append(UserPreferenceDiagnostic(
                        anp_seq=anp_seq,
                        has_preference_documents=has_preference_data,
                        preference_queries_status=diagnostic_result.get("query_status", {}),
                        validation_results=diagnostic_result.get("validation_results", {}),
                        document_count=len(preference_docs),
                        last_processed=last_processed,
                        issues=diagnostic_result.get("issues", []),
                        recommendations=diagnostic_result.get("recommendations", [])
                    ))
                    
            except Exception as e:
                logger.warning(f"Failed to diagnose anp_seq {anp_seq}: {str(e)}")
                continue
        
        return BulkDiagnosticResult(
            total_users_checked=len(users_to_check),
            users_with_issues=users_with_issues,
            users_without_preference_data=users_without_preference_data,
            common_issues=common_issues,
            affected_users=affected_users
        )
        
    except Exception as e:
        logger.error(f"Error in bulk diagnostic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk diagnostic failed: {str(e)}")

@router.post("/test-queries/{anp_seq}", response_model=List[PreferenceQueryTestResult])
async def test_preference_queries(
    anp_seq: int,
    include_sample_data: bool = Query(False, description="Include sample data in response"),
    db_session = Depends(get_async_session)
):
    """
    Test all preference queries for a specific user and return detailed results.
    """
    try:
        query_executor = LegacyQueryExecutor()
        results = []
        
        # Test each preference query
        query_methods = [
            ("imagePreferenceStatsQuery", query_executor.imagePreferenceStatsQuery),
            ("preferenceDataQuery", query_executor.preferenceDataQuery),
            ("preferenceJobsQuery", query_executor.preferenceJobsQuery)
        ]
        
        for query_name, query_method in query_methods:
            start_time = datetime.now()
            success = False
            row_count = 0
            error_message = None
            sample_data = None
            
            try:
                # Execute query
                query_result = await query_method(anp_seq)
                success = True
                row_count = len(query_result) if query_result else 0
                
                # Include sample data if requested and available
                if include_sample_data and query_result:
                    sample_data = query_result[:3]  # First 3 rows
                    
            except Exception as e:
                error_message = str(e)
                logger.warning(f"Query {query_name} failed for anp_seq {anp_seq}: {error_message}")
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            results.append(PreferenceQueryTestResult(
                anp_seq=anp_seq,
                query_name=query_name,
                success=success,
                execution_time_ms=execution_time,
                row_count=row_count,
                error_message=error_message,
                sample_data=sample_data
            ))
        
        return results
        
    except Exception as e:
        logger.error(f"Error testing preference queries for anp_seq {anp_seq}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query testing failed: {str(e)}")

@router.post("/validate-repair/{anp_seq}", response_model=ValidationRepairResult)
async def validate_and_repair_preference_data(
    anp_seq: int,
    force_repair: bool = Query(False, description="Force repair even if validation passes"),
    db_session = Depends(get_async_session)
):
    """
    Validate preference data for a user and attempt repair if issues are found.
    """
    try:
        validator = PreferenceDataValidator()
        diagnostics = PreferenceDiagnostics()
        
        # Perform validation
        validation_result = await validator.validate_user_preference_data(anp_seq)
        issues_found = validation_result.get("issues", [])
        
        repair_attempted = False
        repair_successful = False
        new_documents_created = 0
        error_message = None
        
        # Attempt repair if issues found or forced
        if issues_found or force_repair:
            try:
                repair_attempted = True
                
                # Run repair process (re-process preference data)
                repair_result = await diagnostics.repair_user_preference_data(anp_seq)
                repair_successful = repair_result.get("success", False)
                new_documents_created = repair_result.get("documents_created", 0)
                
                if not repair_successful:
                    error_message = repair_result.get("error", "Unknown repair error")
                    
            except Exception as e:
                error_message = str(e)
                logger.error(f"Repair failed for anp_seq {anp_seq}: {error_message}")
        
        return ValidationRepairResult(
            anp_seq=anp_seq,
            validation_performed=True,
            issues_found=issues_found,
            repair_attempted=repair_attempted,
            repair_successful=repair_successful,
            new_documents_created=new_documents_created,
            error_message=error_message
        )
        
    except Exception as e:
        logger.error(f"Error in validation/repair for anp_seq {anp_seq}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation/repair failed: {str(e)}")

@router.get("/stats/overview")
async def get_preference_data_overview(
    db_session = Depends(get_async_session)
):
    """
    Get overview statistics of preference data across all users.
    """
    try:
        doc_repo = DocumentRepository(db_session)
        
        # Get basic statistics
        total_users = await doc_repo.get_total_user_count()
        users_with_preference_docs = await doc_repo.get_users_with_document_type("PREFERENCE_ANALYSIS")
        
        # Calculate percentages
        preference_coverage = (len(users_with_preference_docs) / total_users * 100) if total_users > 0 else 0
        
        return {
            "total_users": total_users,
            "users_with_preference_documents": len(users_with_preference_docs),
            "preference_data_coverage_percent": round(preference_coverage, 2),
            "users_missing_preference_data": total_users - len(users_with_preference_docs)
        }
        
    except Exception as e:
        logger.error(f"Error getting preference data overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get overview: {str(e)}")