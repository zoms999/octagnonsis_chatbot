import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import DocumentRepository
from database.cache import DocumentCache
from database.models import ChatDocument


@pytest.mark.asyncio
async def test_repository_cache_get_and_invalidate():
    session = Mock(spec=AsyncSession)
    cache = DocumentCache(capacity=10, ttl_seconds=60)
    repo = DocumentRepository(session, cache)

    # Prepare a fake document and session.execute behavior
    doc_id = uuid4()
    document = Mock(spec=ChatDocument)
    document.doc_id = doc_id
    document.user_id = uuid4()
    document.summary_text = "요약"
    document.doc_type = "PERSONALITY_PROFILE"

    result = Mock()
    result.scalar_one_or_none.return_value = document
    session.execute = AsyncMock(return_value=result)

    # First get -> cache miss, fetch from DB
    fetched = await repo.get_document_by_id(doc_id)
    assert fetched is document
    assert session.execute.await_count == 1

    # Second get -> cache hit, no DB call
    fetched2 = await repo.get_document_by_id(doc_id)
    assert fetched2 is document
    assert session.execute.await_count == 1

    # Update document -> invalidates cache and refreshes
    session.execute = AsyncMock(return_value=result)
    updated = await repo.update_document(doc_id, summary_text="새 요약")
    assert updated is not None

    # Next get should hit DB again at least once after invalidation
    session.execute = AsyncMock(return_value=result)
    fetched3 = await repo.get_document_by_id(doc_id)
    assert fetched3 is document
    assert session.execute.await_count >= 1


