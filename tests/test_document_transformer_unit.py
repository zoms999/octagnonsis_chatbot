import pytest
from etl.document_transformer import DocumentTransformer, TransformedDocument, DocumentTransformationError
from database.models import DocumentType


def test_safe_get_and_value():
    dt = DocumentTransformer()
    # _safe_get returns default when list empty
    assert dt._safe_get([], 0, {"x": 1}) == {"x": 1}
    # _safe_get_value returns default when missing
    assert dt._safe_get_value({"a": 1}, "b", 5) == 5


def test_create_personality_profile_minimal():
    dt = DocumentTransformer()
    query_results = {
        "tendencyQuery": [{
            "Tnd1": "창의형", "Tnd1_code": "t1", "Tnd1_explanation": "설명1", "Tnd1_percentage": 12.3,
            "Tnd2": "분석형", "Tnd2_code": "t2", "Tnd2_explanation": "설명2", "Tnd2_percentage": 9.8
        }],
        "topTendencyQuery": [
            {"rank": 1, "tendency_name": "창의형", "code": "t1", "score": 85, "percentage_in_total": 15.2, "description": ""},
            {"rank": 2, "tendency_name": "분석형", "code": "t2", "score": 78, "percentage_in_total": 12.1, "description": ""}
        ],
        "personalityDetailQuery": [{"detail": "d"}],
        "strengthsWeaknessesQuery": [{"strengths": ["a"], "weaknesses": ["b"]}],
    }
    doc = dt._create_personality_profile(query_results)
    assert isinstance(doc, TransformedDocument)
    assert doc.doc_type == DocumentType.PERSONALITY_PROFILE
    assert "primary_tendency" in doc.content
    assert len(doc.summary_text) > 10


def test_thinking_skills_summary_and_levels():
    dt = DocumentTransformer()
    query_results = {
        "thinkingSkillsQuery": [],
        "analyticalThinkingQuery": [{"score": 80, "percentile": 92, "description": ""}],
        "creativityQuery": [{"score": 75, "percentile": 88, "description": ""}],
        "practicalThinkingQuery": [{"score": 60, "percentile": 55, "description": ""}],
        "abstractThinkingQuery": [{"score": 70, "percentile": 65, "description": ""}],
        "problemSolvingQuery": [{"score": 65, "percentile": 58, "description": ""}],
        "memoryQuery": [{"score": 55, "percentile": 49, "description": ""}],
        "attentionQuery": [{"score": 50, "percentile": 40, "description": ""}],
        "processingSpeedQuery": [{"score": 68, "percentile": 60, "description": ""}],
    }
    doc = dt._create_thinking_skills_document(query_results)
    assert doc.doc_type == DocumentType.THINKING_SKILLS
    assert "core_thinking_skills" in doc.content
    assert any(s["korean_name"] for s in doc.content["core_thinking_skills"])  # localized names
    assert len(doc.summary_text) > 10


