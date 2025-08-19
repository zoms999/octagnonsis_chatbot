"""
Comprehensive tests for administrative preference data management tools.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from api.admin_preference_endpoints import (
    UserPreferenceDiagnostic,
    BulkDiagnosticResult,
    PreferenceQueryTestResult,
    ValidationRepairResult
)
from etl.preference_diagnostics import PreferenceDiagnostics
from etl.preference_data_validator import PreferenceDataValidator


class TestAdminPreferenceEndpoints:
    """Test admin preference API endpoints"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_diagnostics(self):
        """Mock preference diagnostics"""
        diagnostics = Mock(spec=PreferenceDiagnostics)
        diagnostics.diagnose_user_preference_data = AsyncMock()
        diagnostics.repair_user_preference_data = AsyncMock()
        return diagnostics
    
    @pytest.fixture
    def mock_validator(self):
        """Mock preference data validator"""
        validator = Mock(spec=PreferenceDataValidator)
        validator.validate_user_preference_data = AsyncMock()
        return validator
    
    @pytest.fixture
    def sample_diagnostic_result(self):
        """Sample diagnostic result"""
        return {
            "anp_seq": 12345,
            "timestamp": datetime.now().isoformat(),
            "query_status": {
                "imagePreferenceStatsQuery": {
                    "success": True,
                    "row_count": 5,
                    "has_data": True
                },
                "preferenceDataQuery": {
                    "success": False,
                    "error": "Connection timeout"
                },
                "preferenceJobsQuery": {
                    "success": True,
                    "row_count": 0,
                    "has_data": False
                }
            },
            "validation_results": {
                "imagePreferenceStats": {
                    "is_valid": True,
                    "issues": []
                }
            },
            "issues": [
                "Preference data query failed: Connection timeout",
                "No data available for preference jobs"
            ],
            "recommendations": [
                "Fix query execution issues for: preferenceDataQuery",
                "Investigate missing data for: preferenceJobsQuery"
            ]
        }
    
    @pytest.mark.asyncio
    async def test_diagnose_user_preference_data_success(
        self, 
        mock_db_session, 
        mock_diagnostics, 
        sample_diagnostic_result
    ):
        """Test successful user preference data diagnosis"""
        # Setup
        anp_seq = 12345
        mock_diagnostics.diagnose_user_preference_data.return_value = sample_diagnostic_result
        
        # Mock document repository
        with patch('api.admin_preference_endpoints.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_documents_by_anp_seq = AsyncMock(return_value=[
                Mock(document_type="PREFERENCE_ANALYSIS", created_at=datetime.now())
            ])
            mock_repo_class.return_value = mock_repo
            
            # Mock PreferenceDiagnostics
            with patch('api.admin_preference_endpoints.PreferenceDiagnostics') as mock_diag_class:
                mock_diag_class.return_value = mock_diagnostics
                
                # Import and test the endpoint function
                from api.admin_preference_endpoints import diagnose_user_preference_data
                
                result = await diagnose_user_preference_data(anp_seq, mock_db_session)
                
                # Assertions
                assert isinstance(result, UserPreferenceDiagnostic)
                assert result.anp_seq == anp_seq
                assert result.has_preference_documents == True
                assert result.document_count == 1
                assert len(result.issues) == 2
                assert len(result.recommendations) == 2
                
                # Verify mock calls
                mock_diagnostics.diagnose_user_preference_data.assert_called_once_with(anp_seq)
                mock_repo.get_documents_by_anp_seq.assert_called_once_with(anp_seq)
    
    @pytest.mark.asyncio
    async def test_diagnose_user_preference_data_failure(self, mock_db_session):
        """Test user preference data diagnosis with failure"""
        anp_seq = 12345
        
        # Mock PreferenceDiagnostics to raise exception
        with patch('api.admin_preference_endpoints.PreferenceDiagnostics') as mock_diag_class:
            mock_diagnostics = Mock()
            mock_diagnostics.diagnose_user_preference_data = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            mock_diag_class.return_value = mock_diagnostics
            
            from api.admin_preference_endpoints import diagnose_user_preference_data
            
            # Should raise HTTPException
            with pytest.raises(Exception):  # FastAPI HTTPException
                await diagnose_user_preference_data(anp_seq, mock_db_session)
    
    @pytest.mark.asyncio
    async def test_bulk_diagnose_preference_issues(self, mock_db_session):
        """Test bulk preference diagnosis"""
        # Mock document repository
        with patch('api.admin_preference_endpoints.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_unique_anp_seqs = AsyncMock(return_value=[12345, 12346, 12347])
            mock_repo.get_documents_by_anp_seq = AsyncMock(return_value=[])
            mock_repo_class.return_value = mock_repo
            
            # Mock PreferenceDiagnostics
            with patch('api.admin_preference_endpoints.PreferenceDiagnostics') as mock_diag_class:
                mock_diagnostics = Mock()
                mock_diagnostics.diagnose_user_preference_data = AsyncMock(return_value={
                    "issues": ["Test issue"],
                    "query_status": {},
                    "validation_results": {},
                    "recommendations": []
                })
                mock_diag_class.return_value = mock_diagnostics
                
                from api.admin_preference_endpoints import bulk_diagnose_preference_issues
                
                result = await bulk_diagnose_preference_issues(
                    limit=10, skip=0, only_issues=False, db_session=mock_db_session
                )
                
                # Assertions
                assert isinstance(result, BulkDiagnosticResult)
                assert result.total_users_checked == 3
                assert result.users_with_issues == 3
                assert result.users_without_preference_data == 3
                assert len(result.affected_users) == 3
    
    @pytest.mark.asyncio
    async def test_test_preference_queries(self, mock_db_session):
        """Test preference query testing endpoint"""
        anp_seq = 12345
        
        # Mock LegacyQueryExecutor
        with patch('api.admin_preference_endpoints.LegacyQueryExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.imagePreferenceStatsQuery = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
            mock_executor.preferenceDataQuery = AsyncMock(side_effect=Exception("Query failed"))
            mock_executor.preferenceJobsQuery = AsyncMock(return_value=[])
            mock_executor_class.return_value = mock_executor
            
            from api.admin_preference_endpoints import test_preference_queries
            
            result = await test_preference_queries(
                anp_seq, include_sample_data=True, db_session=mock_db_session
            )
            
            # Assertions
            assert isinstance(result, list)
            assert len(result) == 3
            
            # Check first query (success)
            assert result[0].anp_seq == anp_seq
            assert result[0].query_name == "imagePreferenceStatsQuery"
            assert result[0].success == True
            assert result[0].row_count == 2
            assert result[0].sample_data is not None
            
            # Check second query (failure)
            assert result[1].query_name == "preferenceDataQuery"
            assert result[1].success == False
            assert result[1].error_message == "Query failed"
            
            # Check third query (empty result)
            assert result[2].query_name == "preferenceJobsQuery"
            assert result[2].success == True
            assert result[2].row_count == 0
    
    @pytest.mark.asyncio
    async def test_validate_and_repair_preference_data(self, mock_db_session):
        """Test preference data validation and repair"""
        anp_seq = 12345
        
        # Mock PreferenceDataValidator
        with patch('api.admin_preference_endpoints.PreferenceDataValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_user_preference_data = AsyncMock(return_value={
                "issues": ["Data quality issue"]
            })
            mock_validator_class.return_value = mock_validator
            
            # Mock PreferenceDiagnostics
            with patch('api.admin_preference_endpoints.PreferenceDiagnostics') as mock_diag_class:
                mock_diagnostics = Mock()
                mock_diagnostics.repair_user_preference_data = AsyncMock(return_value={
                    "success": True,
                    "documents_created": 3,
                    "error": None
                })
                mock_diag_class.return_value = mock_diagnostics
                
                from api.admin_preference_endpoints import validate_and_repair_preference_data
                
                result = await validate_and_repair_preference_data(
                    anp_seq, force_repair=False, db_session=mock_db_session
                )
                
                # Assertions
                assert isinstance(result, ValidationRepairResult)
                assert result.anp_seq == anp_seq
                assert result.validation_performed == True
                assert result.issues_found == ["Data quality issue"]
                assert result.repair_attempted == True
                assert result.repair_successful == True
                assert result.new_documents_created == 3


class TestPreferenceDiagnostics:
    """Test PreferenceDiagnostics class"""
    
    @pytest.fixture
    def diagnostics(self):
        """Create PreferenceDiagnostics instance"""
        return PreferenceDiagnostics()
    
    @pytest.mark.asyncio
    async def test_diagnose_user_preference_data(self, diagnostics):
        """Test user preference data diagnosis"""
        anp_seq = 12345
        
        # Mock dependencies
        with patch('etl.legacy_query_executor.LegacyQueryExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.imagePreferenceStatsQuery = AsyncMock(return_value=[{"stat": "value"}])
            mock_executor.preferenceDataQuery = AsyncMock(return_value=[])
            mock_executor.preferenceJobsQuery = AsyncMock(side_effect=Exception("DB Error"))
            mock_executor_class.return_value = mock_executor
            
            with patch('etl.preference_data_validator.PreferenceDataValidator') as mock_validator_class:
                mock_validator = Mock()
                mock_validator.validate_image_preference_stats = AsyncMock(return_value={
                    "is_valid": True,
                    "issues": []
                })
                mock_validator_class.return_value = mock_validator
                
                result = await diagnostics.diagnose_user_preference_data(anp_seq)
                
                # Assertions
                assert result["anp_seq"] == anp_seq
                assert "query_status" in result
                assert "validation_results" in result
                assert "issues" in result
                assert "recommendations" in result
                
                # Check query status
                assert result["query_status"]["imagePreferenceStatsQuery"]["success"] == True
                assert result["query_status"]["preferenceDataQuery"]["success"] == True
                assert result["query_status"]["preferenceJobsQuery"]["success"] == False
                
                # Check issues
                assert len(result["issues"]) > 0
                assert any("Preference jobs query failed" in issue for issue in result["issues"])
    
    @pytest.mark.asyncio
    async def test_repair_user_preference_data(self, diagnostics):
        """Test user preference data repair"""
        anp_seq = 12345
        
        # Mock database session and repositories
        with patch('database.connection.db_manager') as mock_db_manager:
            mock_db_session = AsyncMock()
            mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_db_session
            
            mock_doc_repo = Mock()
            mock_doc_repo.get_documents_by_anp_seq = AsyncMock(return_value=[
                Mock(document_type="PREFERENCE_ANALYSIS", id="doc1")
            ])
            mock_doc_repo.delete_document = AsyncMock()
            mock_doc_repo.save_document = AsyncMock()
            
            with patch('database.repositories.DocumentRepository', return_value=mock_doc_repo):
                with patch('etl.document_transformer.DocumentTransformer') as mock_transformer_class:
                    mock_transformer = Mock()
                    mock_transformer._chunk_preference_analysis = AsyncMock(return_value=[
                        Mock(),  # Mock document 1
                        Mock(),  # Mock document 2
                    ])
                    mock_transformer_class.return_value = mock_transformer
                    
                    with patch('etl.legacy_query_executor.LegacyQueryExecutor') as mock_executor_class:
                        mock_executor = Mock()
                        mock_executor.imagePreferenceStatsQuery = AsyncMock(return_value=[{"stat": "value"}])
                        mock_executor.preferenceDataQuery = AsyncMock(return_value=[{"pref": "data"}])
                        mock_executor.preferenceJobsQuery = AsyncMock(return_value=[{"job": "info"}])
                        mock_executor_class.return_value = mock_executor
                        
                        with patch('etl.preference_data_validator.PreferenceDataValidator') as mock_validator_class:
                            mock_validator = Mock()
                            mock_validator.validate_user_preference_data = AsyncMock(return_value={
                                "is_valid": True
                            })
                            mock_validator_class.return_value = mock_validator
                            
                            result = await diagnostics.repair_user_preference_data(anp_seq)
                            
                            # Assertions
                            assert result["anp_seq"] == anp_seq
                            assert result["success"] == True
                            assert result["documents_created"] == 2
                            assert result["error"] is None
                            assert len(result["steps_completed"]) > 0
                            
                            # Verify calls
                            mock_doc_repo.delete_document.assert_called_once_with("doc1")
                            assert mock_doc_repo.save_document.call_count == 2


class TestPreferenceDataValidator:
    """Test PreferenceDataValidator class"""
    
    @pytest.fixture
    def validator(self):
        """Create PreferenceDataValidator instance"""
        return PreferenceDataValidator()
    
    @pytest.mark.asyncio
    async def test_validate_user_preference_data_success(self, validator):
        """Test successful user preference data validation"""
        anp_seq = 12345
        
        # Mock LegacyQueryExecutor
        with patch('etl.preference_data_validator.LegacyQueryExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.imagePreferenceStatsQuery = AsyncMock(return_value=[{"valid": "data"}])
            mock_executor.preferenceDataQuery = AsyncMock(return_value=[{"valid": "data"}])
            mock_executor.preferenceJobsQuery = AsyncMock(return_value=[{"valid": "data"}])
            mock_executor_class.return_value = mock_executor
            
            # Mock validation methods
            validator.validate_image_preference_stats = AsyncMock(return_value={
                "is_valid": True,
                "issues": []
            })
            validator.validate_preference_data = AsyncMock(return_value={
                "is_valid": True,
                "issues": []
            })
            validator.validate_preference_jobs = AsyncMock(return_value={
                "is_valid": True,
                "issues": []
            })
            
            result = await validator.validate_user_preference_data(anp_seq)
            
            # Assertions
            assert result["anp_seq"] == anp_seq
            assert result["is_valid"] == True
            assert len(result["issues"]) == 0
            assert "validation_details" in result
            assert len(result["validation_details"]) == 3
    
    @pytest.mark.asyncio
    async def test_validate_user_preference_data_with_issues(self, validator):
        """Test user preference data validation with issues"""
        anp_seq = 12345
        
        # Mock LegacyQueryExecutor
        with patch('etl.preference_data_validator.LegacyQueryExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.imagePreferenceStatsQuery = AsyncMock(return_value=[{"invalid": "data"}])
            mock_executor.preferenceDataQuery = AsyncMock(side_effect=Exception("Query failed"))
            mock_executor.preferenceJobsQuery = AsyncMock(return_value=[])
            mock_executor_class.return_value = mock_executor
            
            # Mock validation methods
            validator.validate_image_preference_stats = AsyncMock(return_value={
                "is_valid": False,
                "issues": ["Invalid data format"]
            })
            validator.validate_preference_data = AsyncMock()  # Won't be called due to exception
            validator.validate_preference_jobs = AsyncMock(return_value={
                "is_valid": True,
                "issues": []
            })
            
            result = await validator.validate_user_preference_data(anp_seq)
            
            # Assertions
            assert result["anp_seq"] == anp_seq
            assert result["is_valid"] == False
            assert len(result["issues"]) >= 2  # At least validation issue + query failure
            assert any("Invalid data format" in issue for issue in result["issues"])
            assert any("Preference data validation failed" in issue for issue in result["issues"])


class TestAdminPreferenceCLI:
    """Test command-line administrative tool"""
    
    @pytest.fixture
    def mock_cli(self):
        """Mock CLI instance"""
        from admin_preference_cli import PreferenceAdminCLI
        cli = PreferenceAdminCLI()
        cli.diagnostics = Mock()
        cli.validator = Mock()
        return cli
    
    @pytest.mark.asyncio
    async def test_diagnose_user_success(self, mock_cli, capsys):
        """Test CLI user diagnosis with success"""
        anp_seq = 12345
        
        # Mock diagnostic result
        mock_cli.diagnostics.diagnose_user_preference_data = AsyncMock(return_value={
            "query_status": {
                "imagePreferenceStatsQuery": {"success": True, "row_count": 5, "has_data": True},
                "preferenceDataQuery": {"success": False, "error": "Connection timeout"}
            },
            "issues": ["Preference data query failed: Connection timeout"],
            "recommendations": ["Fix query execution issues"],
            "validation_results": {}
        })
        
        await mock_cli.diagnose_user(anp_seq, verbose=False)
        
        # Check output
        captured = capsys.readouterr()
        assert f"Diagnosing preference data for user {anp_seq}" in captured.out
        assert "✅ imagePreferenceStatsQuery" in captured.out
        assert "❌ preferenceDataQuery" in captured.out
        assert "Issues Found (1)" in captured.out
        assert "Recommendations:" in captured.out
    
    @pytest.mark.asyncio
    async def test_test_queries_success(self, mock_cli, capsys):
        """Test CLI query testing with success"""
        anp_seq = 12345
        
        # Mock query executor
        with patch('admin_preference_cli.LegacyQueryExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.imagePreferenceStatsQuery = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
            mock_executor.preferenceDataQuery = AsyncMock(side_effect=Exception("Query failed"))
            mock_executor.preferenceJobsQuery = AsyncMock(return_value=[])
            mock_executor_class.return_value = mock_executor
            
            await mock_cli.test_queries(anp_seq, include_sample=True)
            
            # Check output
            captured = capsys.readouterr()
            assert f"Testing preference queries for user {anp_seq}" in captured.out
            assert "✅ Image Preference Stats" in captured.out
            assert "❌ Preference Data" in captured.out
            assert "Row Count: 2" in captured.out
            assert "Sample Data" in captured.out
    
    @pytest.mark.asyncio
    async def test_repair_user_success(self, mock_cli, capsys):
        """Test CLI user repair with success"""
        anp_seq = 12345
        
        # Mock diagnostic and repair results
        mock_cli.diagnostics.diagnose_user_preference_data = AsyncMock(return_value={
            "issues": ["Test issue"]
        })
        mock_cli.diagnostics.repair_user_preference_data = AsyncMock(return_value={
            "success": True,
            "documents_created": 3,
            "steps_completed": ["Step 1", "Step 2", "Step 3"],
            "error": None
        })
        
        await mock_cli.repair_user(anp_seq, force=False)
        
        # Check output
        captured = capsys.readouterr()
        assert f"Repairing preference data for user {anp_seq}" in captured.out
        assert "Found 1 issues. Proceeding with repair" in captured.out
        assert "✅ Repair Successful!" in captured.out
        assert "Documents Created: 3" in captured.out
    
    @pytest.mark.asyncio
    async def test_system_overview(self, mock_cli, capsys):
        """Test CLI system overview"""
        # Mock database session and repository
        with patch('admin_preference_cli.get_db_session') as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session
            
            with patch('admin_preference_cli.DocumentRepository') as mock_repo_class:
                mock_repo = Mock()
                mock_repo.get_total_user_count = AsyncMock(return_value=1000)
                mock_repo.get_users_with_document_type = AsyncMock(return_value=list(range(800)))
                mock_repo_class.return_value = mock_repo
                
                await mock_cli.system_overview()
                
                # Check output
                captured = capsys.readouterr()
                assert "System Preference Data Overview" in captured.out
                assert "Total Users: 1000" in captured.out
                assert "Users with Preference Documents: 800" in captured.out
                assert "Preference Data Coverage: 80.0%" in captured.out
                assert "🟡 Good" in captured.out  # 80% coverage = Good


if __name__ == "__main__":
    pytest.main([__file__])