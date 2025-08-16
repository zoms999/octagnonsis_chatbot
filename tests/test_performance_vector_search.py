import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from database.vector_search import VectorSearchService, SearchQuery, SimilarityMetric
from database.models import ChatDocument


@pytest.mark.asyncio
async def test_vector_search_benchmark_smoke():
    # Mock DB session with minimal response
    session = Mock(spec=AsyncSession)
    result = Mock()
    doc = Mock(spec=ChatDocument)
    doc.created_at = __import__("datetime").datetime.now()
    doc.doc_type = "PERSONALITY_PROFILE"
    doc.summary_text = "요약"
    result.fetchall.return_value = [(doc, 0.9)]
    session.execute = AsyncMock(return_value=result)

    service = VectorSearchService(session)
    q = SearchQuery(user_id=uuid4(), query_vector=[0.01]*768, similarity_metric=SimilarityMetric.COSINE)
    stats = await service.benchmark_query(q, runs=3)

    assert stats["runs"] == 3
    assert stats["avg_ms"] >= 0
    assert stats["min_ms"] >= 0
    assert stats["max_ms"] >= 0


