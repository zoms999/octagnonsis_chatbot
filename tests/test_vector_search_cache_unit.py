import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from database.vector_search import VectorSearchService, SearchQuery, SimilarityMetric
from database.models import ChatDocument


@pytest.mark.asyncio
async def test_vector_search_result_cache_hit(monkeypatch):
    # Mock session.execute to ensure it's called only once thanks to cache
    mock_session = Mock(spec=AsyncSession)
    mock_execute = AsyncMock()

    # Create fake rows [(ChatDocument, similarity)]
    doc = Mock(spec=ChatDocument)
    doc.created_at = __import__("datetime").datetime.now()
    doc.doc_type = "PERSONALITY_PROFILE"
    doc.summary_text = "요약"
    rows = [(doc, 0.9)]

    result_obj = Mock()
    result_obj.fetchall.return_value = rows
    mock_execute.return_value = result_obj
    mock_session.execute = mock_execute

    service = VectorSearchService(mock_session)

    q = SearchQuery(
        user_id=uuid4(),
        query_vector=[0.01] * 768,
        similarity_metric=SimilarityMetric.COSINE,
        limit=3,
        similarity_threshold=0.1,
    )

    # First call misses cache and executes query
    r1 = await service.similarity_search(q)
    assert len(r1) == 1
    assert mock_session.execute.await_count == 1

    # Second call should be served from cache (no new execute)
    r2 = await service.similarity_search(q)
    assert len(r2) == 1
    assert mock_session.execute.await_count == 1


