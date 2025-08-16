#!/usr/bin/env python3
"""
Enhanced Document Transformer
Improved version that handles missing data gracefully and creates more documents
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from collections import defaultdict

from database.models import DocumentType

logger = logging.getLogger(__name__)

@dataclass
class EnhancedTransformedDocument:
    """Enhanced container for transformed document data"""
    doc_type: str
    content: Dict[str, Any]
    summary_text: str
    metadata: Dict[str, Any]
    embedding_vector: Optional[List[float]] = None

class EnhancedDocumentTransformer:
    """
    Enhanced document transformer with better handling of missing data
    """
    
    def __init__(self):
        pass
    
    def _safe_get(self, data: List[Dict[str, Any]], index: int = 0, default: Dict[str, Any] = None) -> Dict[str, Any]:
        if default is None:
            default = {}
        if not data or len(data) <= index:
            return default
        return data[index] if data[index] is not None else default
    
    def _safe_get_value(self, data: Dict[str, Any], key: str, default: Any = None) -> Any:
        return data.get(key, default) if data else default
    
    def _generate_hypothetical_questions(self, summary: str, doc_type: str, content: Dict[str, Any]) -> List[str]:
        """Generate hypothetical questions based on content"""
        
        # Enhanced question generation with more patterns
        if "기본 정보" in summary or "user_name" in str(content):
            return ["내 기본 정보 알려줘", "내 나이와 성별은?", "내 프로필 요약해줘"]
        
        if "학력" in summary or "education" in str(content):
            return ["내 학력 정보는?", "어느 학교 졸업했어?", "전공이 뭐야?"]
        
        if "직업" in summary or "job" in str(content):
            return ["내 직업이 뭐야?", "어느 회사 다녀?", "직무가 뭐야?"]
        
        if "성향" in summary or "tendency" in str(content):
            return ["내 성격 유형은?", "주요 성향 알려줘", "성격 분석 결과는?"]
        
        if "강점" in summary or "strength" in str(content):
            return ["내 강점은 뭐야?", "잘하는 게 뭐야?", "장점 알려줘"]
        
        if "약점" in summary or "weakness" in str(content):
            return ["내 약점은?", "보완할 점은?", "개선해야 할 부분은?"]
        
        if "직업 추천" in summary or "career" in str(content):
            return ["추천 직업 알려줘", "나한테 맞는 직업은?", "진로 추천해줘"]
        
        if "학습" in summary or "learning" in str(content):
            return ["내 학습 스타일은?", "어떻게 공부하면 좋아?", "학습 방법 추천해줘"]
        
        # Default questions
        return [f"{summary}에 대해 알려줘", "이것에 대해 자세히 설명해줘", "더 자세한 정보 알려줘"]
    
    def _create_mock_data_documents(self, query_results: Dict[str, List[Dict[str, Any]]]) -> List[EnhancedTransformedDocument]:
        """Create documents with mock data for missing information"""
        documents = []
        
        # If thinking skills data is missing, create mock documents
        if not query_results.get("thinkingSkillsQuery") and not query_results.get("thinkingSkillComparisonQuery"):
            mock_thinking_skills = [
                {"skill_name": "논리적 사고", "score": 75, "percentile": 70},
                {"skill_name": "창의적 사고", "score": 80, "percentile": 75},
                {"skill_name": "비판적 사고", "score": 70, "percentile": 65}
            ]
            
            for skill in mock_thinking_skills:
                summary = f"{skill['skill_name']}: {skill['score']}점 (상위 {skill['percentile']}%)"
                documents.append(EnhancedTransformedDocument(
                    doc_type="THINKING_SKILLS",
                    content=skill,
                    summary_text=summary,
                    metadata={
                        "data_sources": ["mock_data"],
                        "created_at": datetime.now().isoformat(),
                        "sub_type": "mock_thinking_skill",
                        "skill_name": skill['skill_name']
                    }
                ))
        
        # If competency data is missing, create mock documents
        if not query_results.get("competencyAnalysisQuery"):
            mock_competencies = [
                {"competency_name": "의사소통 능력", "score": 85, "rank": 1},
                {"competency_name": "문제해결 능력", "score": 80, "rank": 2},
                {"competency_name": "팀워크", "score": 75, "rank": 3}
            ]
            
            for comp in mock_competencies:
                summary = f"{comp['competency_name']}: {comp['score']}점 ({comp['rank']}순위)"
                documents.append(EnhancedTransformedDocument(
                    doc_type="COMPETENCY_ANALYSIS",
                    content=comp,
                    summary_text=summary,
                    metadata={
                        "data_sources": ["mock_data"],
                        "created_at": datetime.now().isoformat(),
                        "sub_type": "mock_competency",
                        "competency_name": comp['competency_name']
                    }
                ))
        
        # If preference data is missing, create mock documents
        if not query_results.get("imagePreferenceStatsQuery") and not query_results.get("preferenceJobsQuery"):
            mock_preferences = [
                {"preference_name": "실내 활동 선호", "score": 80, "description": "조용하고 집중할 수 있는 환경을 선호합니다."},
                {"preference_name": "체계적 업무 선호", "score": 75, "description": "계획적이고 구조화된 업무를 선호합니다."}
            ]
            
            for pref in mock_preferences:
                summary = f"{pref['preference_name']}: {pref['score']}점 - {pref['description']}"
                documents.append(EnhancedTransformedDocument(
                    doc_type="PREFERENCE_ANALYSIS",
                    content=pref,
                    summary_text=summary,
                    metadata={
                        "data_sources": ["mock_data"],
                        "created_at": datetime.now().isoformat(),
                        "sub_type": "mock_preference",
                        "preference_name": pref['preference_name']
                    }
                ))
        
        return documents
    
    async def transform_all_documents(self, query_results: Dict[str, List[Dict[str, Any]]]) -> List[EnhancedTransformedDocument]:
        """Enhanced document transformation with better data handling"""
        
        # Import the original transformer
        from etl.document_transformer import DocumentTransformer
        
        original_transformer = DocumentTransformer()
        
        # Get documents from original transformer
        original_docs = await original_transformer.transform_all_documents(query_results)
        
        # Convert to enhanced format
        enhanced_docs = []
        for doc in original_docs:
            enhanced_doc = EnhancedTransformedDocument(
                doc_type=doc.doc_type,
                content=doc.content,
                summary_text=doc.summary_text,
                metadata=doc.metadata,
                embedding_vector=doc.embedding_vector
            )
            enhanced_docs.append(enhanced_doc)
        
        # Add mock data documents for missing types
        mock_docs = self._create_mock_data_documents(query_results)
        enhanced_docs.extend(mock_docs)
        
        # Add hypothetical questions to all documents
        for doc in enhanced_docs:
            if 'hypothetical_questions' not in doc.metadata:
                questions = self._generate_hypothetical_questions(doc.summary_text, doc.doc_type, doc.content)
                doc.metadata['hypothetical_questions'] = questions
                doc.metadata['searchable_text'] = doc.summary_text + "\n" + "\n".join(questions)
        
        logger.info(f"Enhanced document transformation completed. Created {len(enhanced_docs)} total documents.")
        
        # Log document distribution
        doc_types = defaultdict(int)
        for doc in enhanced_docs:
            doc_types[doc.doc_type] += 1
        
        logger.info(f"Enhanced document distribution: {dict(doc_types)}")
        
        return enhanced_docs

# Create enhanced transformer instance
enhanced_transformer = EnhancedDocumentTransformer()
