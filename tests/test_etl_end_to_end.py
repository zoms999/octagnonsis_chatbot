#!/usr/bin/env python3
"""
End-to-End ETL Pipeline Test
Comprehensive test for the complete ETL processing pipeline
"""

import asyncio
import logging
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import uuid
import pytest

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
from etl.logging_config import setup_etl_logging, get_etl_logger, ETLLogContext

setup_etl_logging(log_level="DEBUG", enable_file_logging=False)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_etl_orchestrator():
    """Test the ETL orchestrator with mock data"""
    try:
        from etl.etl_orchestrator import ETLOrchestrator, ValidationLevel, ETLContext
        from etl.test_completion_handler import JobTracker, JobStatus
        from database.models import ChatUser
        
        logger.info("Testing ETL Orchestrator...")
        
        # Note: Using database-based job tracking instead of Redis
        job_tracker = JobTracker()
        
        # Create test context
        job_id = str(uuid.uuid4())
        user_id = "test_user_orchestrator"
        anp_seq = 99999
        
        # Initialize orchestrator
        orchestrator = ETLOrchestrator(
            validation_level=ValidationLevel.BASIC,  # Use basic validation for testing
            enable_rollback=True,
            max_retries_per_stage=1
        )
        
        logger.info(f"Created orchestrator with job_id: {job_id}")
        
        # Note: This test would need a real database session to work fully
        # For now, we'll test the orchestrator initialization and validation logic
        
        # Test data validator
        from etl.etl_orchestrator import DataValidator
        from etl.legacy_query_executor import QueryResult
        
        # Create mock query results
        mock_query_results = {
            "tendencyQuery": QueryResult(
                query_name="tendencyQuery",
                success=True,
                data=[{"Tnd1": "창의형", "Tnd2": "분석형"}],
                execution_time=1.5,
                row_count=1
            ),
            "thinkingSkillsQuery": QueryResult(
                query_name="thinkingSkillsQuery",
                success=True,
                data=[
                    {"skill_name": "논리적 사고", "score": 85, "percentile": 75},
                    {"skill_name": "창의적 사고", "score": 90, "percentile": 85}
                ],
                execution_time=2.0,
                row_count=2
            ),
            "careerRecommendationQuery": QueryResult(
                query_name="careerRecommendationQuery",
                success=True,
                data=[
                    {"job_code": "job001", "job_name": "소프트웨어 개발자", "match_score": 92},
                    {"job_code": "job002", "job_name": "데이터 분석가", "match_score": 87}
                ],
                execution_time=1.8,
                row_count=2
            ),
            "failedQuery": QueryResult(
                query_name="failedQuery",
                success=False,
                error="Connection timeout",
                execution_time=5.0
            )
        }
        
        # Test query validation
        validation_results = DataValidator.validate_query_results(
            mock_query_results, ValidationLevel.BASIC
        )
        
        logger.info(f"Query validation results: {json.dumps(validation_results, indent=2)}")
        
        if validation_results["passed"]:
            logger.info("✓ Query validation passed")
        else:
            logger.error("✗ Query validation failed")
            return False
        
        # Test document validation
        from etl.document_transformer import TransformedDocument
        
        mock_documents = [
            TransformedDocument(
                doc_type="PERSONALITY_PROFILE",
                content={
                    "primary_tendency": {"name": "창의형", "code": "tnd12000"},
                    "secondary_tendency": {"name": "분석형", "code": "tnd21000"}
                },
                summary_text="사용자의 주요 성향은 창의형이며, 부성향은 분석형입니다.",
                metadata={"version": "1.0"}
            ),
            TransformedDocument(
                doc_type="THINKING_SKILLS",
                content={
                    "core_thinking_skills": [
                        {"skill_name": "논리적 사고", "score": 85, "percentile": 75}
                    ]
                },
                summary_text="사용자의 논리적 사고 능력은 우수한 수준입니다.",
                metadata={"version": "1.0"}
            )
        ]
        
        doc_validation_results = DataValidator.validate_transformed_documents(
            mock_documents, ValidationLevel.BASIC
        )
        
        logger.info(f"Document validation results: {json.dumps(doc_validation_results, indent=2)}")
        
        if doc_validation_results["passed"]:
            logger.info("✓ Document validation passed")
        else:
            logger.error("✗ Document validation failed")
            return False
        
        # Test embedding validation
        mock_embedded_documents = [
            {
                "doc_type": "PERSONALITY_PROFILE",
                "content": {"test": "data"},
                "summary_text": "Test summary",
                "embedding_vector": [0.1, 0.2, 0.3, 0.4, 0.5] * 100,  # 500-dim vector
                "metadata": {}
            },
            {
                "doc_type": "THINKING_SKILLS",
                "content": {"test": "data"},
                "summary_text": "Test summary",
                "embedding_vector": [0.2, 0.3, 0.4, 0.5, 0.6] * 100,  # 500-dim vector
                "metadata": {}
            }
        ]
        
        embedding_validation_results = DataValidator.validate_embeddings(
            mock_embedded_documents, ValidationLevel.BASIC
        )
        
        logger.info(f"Embedding validation results: {json.dumps(embedding_validation_results, indent=2)}")
        
        if embedding_validation_results["passed"]:
            logger.info("✓ Embedding validation passed")
        else:
            logger.error("✗ Embedding validation failed")
            return False
        
        logger.info("✓ ETL Orchestrator validation tests passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ ETL Orchestrator test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_logging_system():
    """Test the ETL logging system"""
    try:
        logger.info("Testing ETL Logging System...")
        
        # Test context logger
        etl_logger = get_etl_logger(
            __name__,
            job_id="test_job_logging",
            user_id="test_user_logging",
            stage="testing"
        )
        
        etl_logger.info("Testing context logger")
        etl_logger.warning("Testing warning with context")
        
        # Test context manager
        with ETLLogContext(logger, "test operation", job_id="test_job_logging"):
            await asyncio.sleep(0.1)  # Simulate work
            logger.info("Work completed inside context")
        
        # Test metrics logging
        from etl.logging_config import log_etl_metrics
        
        log_etl_metrics(
            logger,
            {
                "test_metric": 42,
                "processing_time": 1.5,
                "success_rate": 0.95
            },
            job_id="test_job_logging"
        )
        
        logger.info("✓ Logging system test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Logging system test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_data_validation():
    """Test comprehensive data validation"""
    try:
        from etl.etl_orchestrator import DataValidator, ValidationLevel
        from etl.legacy_query_executor import QueryResult
        
        logger.info("Testing Data Validation...")
        
        # Test with various validation levels
        test_query_results = {
            "tendencyQuery": QueryResult(
                query_name="tendencyQuery",
                success=True,
                data=[{"Tnd1": "창의형", "Tnd2": "분석형"}],
                execution_time=1.0,
                row_count=1
            ),
            "thinkingSkillsQuery": QueryResult(
                query_name="thinkingSkillsQuery",
                success=True,
                data=[
                    {"skill_name": "논리적 사고", "score": 85, "percentile": 75},
                    {"skill_name": "창의적 사고", "score": -10, "percentile": 150}  # Invalid data
                ],
                execution_time=1.0,
                row_count=2
            ),
            "careerRecommendationQuery": QueryResult(
                query_name="careerRecommendationQuery",
                success=False,
                error="Database connection failed",
                execution_time=5.0
            )
        }
        
        # Test BASIC validation (should pass)
        basic_results = DataValidator.validate_query_results(
            test_query_results, ValidationLevel.BASIC
        )
        logger.info(f"Basic validation: {'PASSED' if basic_results['passed'] else 'FAILED'}")
        
        # Test STANDARD validation (should fail due to missing critical query)
        standard_results = DataValidator.validate_query_results(
            test_query_results, ValidationLevel.STANDARD
        )
        logger.info(f"Standard validation: {'PASSED' if standard_results['passed'] else 'FAILED'}")
        
        # Test STRICT validation (should fail)
        strict_results = DataValidator.validate_query_results(
            test_query_results, ValidationLevel.STRICT
        )
        logger.info(f"Strict validation: {'PASSED' if strict_results['passed'] else 'FAILED'}")
        
        # Verify that validation correctly identifies issues
        if (basic_results['passed'] and 
            not standard_results['passed'] and 
            not strict_results['passed']):
            logger.info("✓ Data validation levels working correctly")
            return True
        else:
            logger.error("✗ Data validation levels not working as expected")
            return False
        
    except Exception as e:
        logger.error(f"✗ Data validation test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_error_handling_and_rollback():
    """Test error handling and rollback mechanisms"""
    try:
        from etl.etl_orchestrator import ETLValidationError, ETLRollbackError, ETLStage
        
        logger.info("Testing Error Handling and Rollback...")
        
        # Test validation error creation
        try:
            raise ETLValidationError(
                ETLStage.DATA_VALIDATION,
                "Test validation error",
                {"test": "validation_results"}
            )
        except ETLValidationError as e:
            logger.info(f"✓ ETLValidationError created correctly: {e}")
        
        # Test rollback error creation
        try:
            raise ETLRollbackError(
                ETLStage.DOCUMENT_STORAGE,
                "Test rollback error"
            )
        except ETLRollbackError as e:
            logger.info(f"✓ ETLRollbackError created correctly: {e}")
        
        logger.info("✓ Error handling test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error handling test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_job_tracking_integration():
    """Test job tracking integration"""
    try:
        from etl.test_completion_handler import JobTracker, JobProgress, JobStatus
        
        logger.info("Testing Job Tracking Integration...")
        
        # Note: Using database-based job tracking instead of Redis
        logger.info("✓ Database-based job tracking initialized")
        
        # Initialize job tracker
        job_tracker = JobTracker()
        
        # Create test job
        job_id = str(uuid.uuid4())
        job_progress = JobProgress(
            job_id=job_id,
            user_id="test_user_integration",
            anp_seq=88888,
            status=JobStatus.PENDING,
            progress_percentage=0.0,
            current_step="Testing job tracking integration",
            total_steps=5,
            completed_steps=0,
            started_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Test job creation and updates
        await job_tracker.create_job(job_progress)
        logger.info(f"✓ Job created: {job_id}")
        
        # Test job updates
        for step in range(1, 6):
            await job_tracker.update_job(
                job_id,
                progress_percentage=step * 20.0,
                current_step=f"Step {step} completed",
                completed_steps=step
            )
            logger.info(f"✓ Job updated: step {step}")
        
        # Mark as completed
        await job_tracker.update_job(
            job_id,
            status=JobStatus.SUCCESS.value,
            progress_percentage=100.0,
            completed_at=datetime.now().isoformat()
        )
        
        # Verify final state
        final_job = await job_tracker.get_job(job_id)
        if final_job and final_job.status == JobStatus.SUCCESS:
            logger.info("✓ Job tracking integration test passed")
            
            # Cleanup
            await job_tracker.delete_job(job_id)
            return True
        else:
            logger.error("✗ Job tracking integration test failed")
            return False
        
    except Exception as e:
        logger.error(f"✗ Job tracking integration test failed: {e}")
        return False

@pytest.mark.asyncio
async def test_configuration_and_environment():
    """Test configuration and environment setup"""
    try:
        logger.info("Testing Configuration and Environment...")
        
        # Test environment variable handling
        test_vars = {
            'ETL_VALIDATION_LEVEL': 'standard',
            'ETL_ENABLE_ROLLBACK': 'true',
            'ETL_MAX_RETRIES_PER_STAGE': '2',

            'DATABASE_URL': 'postgresql+asyncpg://user:password@localhost/aptitude_chatbot'
        }
        
        for var, expected_value in test_vars.items():
            actual_value = os.getenv(var, expected_value)  # Use expected as default
            logger.info(f"Environment variable {var}: {actual_value}")
        
        # Test ETL configuration
        try:
            from etl.config import ETL_CONFIG, EMBEDDING_CONFIG
            
            logger.info(f"ETL Config: {json.dumps(ETL_CONFIG, indent=2)}")
            logger.info(f"Embedding Config: {json.dumps(EMBEDDING_CONFIG, indent=2)}")
            
            logger.info("✓ Configuration loading test passed")
            
        except ImportError as e:
            logger.warning(f"Configuration import failed (expected in test environment): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False

async def run_comprehensive_etl_tests():
    """Run all ETL end-to-end tests"""
    logger.info("=" * 80)
    logger.info("Starting Comprehensive ETL End-to-End Tests")
    logger.info("=" * 80)
    
    tests = [
        ("Configuration and Environment", test_configuration_and_environment),
        ("Logging System", test_logging_system),
        ("Data Validation", test_data_validation),
        ("Error Handling and Rollback", test_error_handling_and_rollback),
        ("Job Tracking Integration", test_job_tracking_integration),
        ("ETL Orchestrator", test_etl_orchestrator),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*20} Running {test_name} Test {'='*20}")
        
        try:
            with ETLLogContext(logger, f"{test_name} test"):
                result = await test_func()
                results[test_name] = result
                status = "PASSED" if result else "FAILED"
                logger.info(f"{test_name}: {status}")
        except Exception as e:
            logger.error(f"{test_name}: FAILED with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Test Results Summary")
    logger.info("=" * 80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All ETL end-to-end tests passed!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed")
        return False

def main():
    """Main entry point"""
    # Set default environment variables for testing

    os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://user:password@localhost/aptitude_chatbot')
    os.environ.setdefault('ETL_VALIDATION_LEVEL', 'standard')
    os.environ.setdefault('ETL_ENABLE_ROLLBACK', 'true')
    
    try:
        success = asyncio.run(run_comprehensive_etl_tests())
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())