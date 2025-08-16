import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from uuid import uuid4

from rag.question_processor import QuestionProcessor
from rag.context_builder import ContextBuilder
from rag.response_generator import ResponseGenerator
from database.vector_search import VectorSearchService, SearchQuery
from database.models import ChatDocument


class StubEmbedder:
    async def generate_embedding(self, text: str):
        # Return 768-dim vector
        return [0.01] * 768


@pytest.mark.asyncio
async def test_rag_pipeline_end_to_end_with_stubs(monkeypatch):
    # Prepare stubs/mocks
    embedder = StubEmbedder()
    qp = QuestionProcessor(embedder)

    # Mock VectorSearchService
    vss = Mock(spec=VectorSearchService)
    # Create a fake ChatDocument
    doc = Mock(spec=ChatDocument)
    doc.doc_id = uuid4()
    doc.user_id = uuid4()
    doc.doc_type = "PERSONALITY_PROFILE"
    doc.summary_text = "주요 성향: 창의형, 보조 성향: 분석형"
    doc.content = {
        "primary_tendency": {"name": "창의형"},
        "secondary_tendency": {"name": "분석형"},
        "top_tendencies": [{"name": "창의형", "score": 85}, {"name": "분석형", "score": 78}],
    }
    doc.created_at = __import__("datetime").datetime.now()

    sr = type("SR", (), {})()
    sr.document = doc
    sr.similarity_score = 0.92
    vss.similarity_search = AsyncMock(return_value=[sr])

    cb = ContextBuilder(vss)

    # Patch Gemini client and ResponseGenerator
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'test'}):
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                rg = ResponseGenerator()
                # Avoid real API call
                rg._call_gemini_api = AsyncMock(return_value="통합 테스트 응답")

                # Run pipeline
                processed = await qp.process_question("내 성격을 설명해줘", str(uuid4()))
                ctx = await cb.build_context(processed, str(uuid4()))
                resp = await rg.generate_response(ctx, "user1")

                assert resp.content.startswith("통합 테스트 응답")
                assert resp.confidence_score >= 0.0
                assert len(resp.retrieved_doc_ids) >= 0


