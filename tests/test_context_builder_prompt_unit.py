import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from database.vector_search import VectorSearchService, SearchQuery
from rag.context_builder import ContextBuilder, PromptTemplate, RetrievedDocument
from rag.question_processor import ProcessedQuestion, QuestionCategory, QuestionIntent
from database.models import ChatDocument


class DummyProcessed:
    def __init__(self):
        self.original_text = "내 성격을 설명해줘"
        self.embedding_vector = [0.01] * 768
        self.requires_specific_docs = []
        self.category = QuestionCategory.PERSONALITY
        self.intent = QuestionIntent.EXPLAIN
        self.keywords = ["성격", "창의"]
        self.confidence_score = 0.8


@pytest.mark.asyncio
async def test_context_builder_prompt_selection_and_format():
    # Mock vector search to return a single document
    mock_service = Mock(spec=VectorSearchService)
    doc = Mock(spec=ChatDocument)
    doc.doc_id = uuid4()
    doc.doc_type = "PERSONALITY_PROFILE"
    doc.summary_text = "주요 성향: 창의형, 보조 성향: 분석형"
    doc.content = {"primary_tendency": {"name": "창의형"}}
    doc.created_at = __import__("datetime").datetime.now()

    search_result = Mock()
    search_result.document = doc
    search_result.similarity_score = 0.9

    mock_service.similarity_search = AsyncMock(return_value=[search_result])

    builder = ContextBuilder(mock_service)
    processed = DummyProcessed()

    ctx = await builder.build_context(processed, str(uuid4()))
    assert ctx.prompt_template == PromptTemplate.PERSONALITY_EXPLAIN
    assert "검사 결과" in ctx.formatted_prompt
    assert ctx.token_count_estimate > 0


