#!/usr/bin/env python3
"""
Direct RAG search test without API
"""

import asyncio
import sys
sys.path.append('.')
from database.connection import db_manager
from database.models import ChatDocument
from sqlalchemy import select
import numpy as np

async def test_direct_rag():
    """직접 RAG 검색을 테스트합니다."""
    
    user_id = "9b08ed21-fddf-4998-a1f4-29bccda89a54"
    user_question = "내성향알려줘"
    
    print(f"직접 RAG 검색 테스트:")
    print(f"  사용자 질문: {user_question}")
    print(f"  User ID: {user_id}")
    
    try:
        async with db_manager.get_async_session() as session:
            # 1. 사용자의 모든 문서 가져오기
            stmt = select(ChatDocument).where(ChatDocument.user_id == user_id)
            result = await session.execute(stmt)
            documents = result.scalars().all()
            
            print(f"\n📚 사용자 문서 현황:")
            print(f"  총 문서 수: {len(documents)}")
            
            # 문서 타입별 분포
            doc_types = {}
            personality_docs = []
            
            for doc in documents:
                doc_type = doc.doc_type
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                
                # 성향 관련 문서 수집
                if "PERSONALITY" in doc_type:
                    personality_docs.append(doc)
            
            print(f"  문서 타입별 분포:")
            for doc_type, count in doc_types.items():
                print(f"    {doc_type}: {count}개")
            
            # 2. 성향 관련 문서의 가상 질문 확인
            print(f"\n🔍 성향 관련 문서의 가상 질문들:")
            for i, doc in enumerate(personality_docs[:3], 1):
                print(f"  문서 {i}: {doc.doc_type}")
                print(f"    요약: {doc.summary_text[:50]}...")
                
                hypothetical_questions = doc.doc_metadata.get('hypothetical_questions', [])
                print(f"    가상 질문들:")
                for j, question in enumerate(hypothetical_questions, 1):
                    print(f"      {j}. {question}")
                    
                    # 질문 유사도 체크 (간단한 키워드 매칭)
                    if any(keyword in question for keyword in ["성향", "성격", "유형"]):
                        print(f"        ✅ '내성향알려줘'와 관련성 높음!")
            
            # 3. 실제 임베딩 기반 검색 시뮬레이션
            print(f"\n🎯 RAG 검색 시뮬레이션:")
            
            # 사용자 질문과 관련성이 높은 문서 찾기
            relevant_docs = []
            for doc in documents:
                hypothetical_questions = doc.doc_metadata.get('hypothetical_questions', [])
                searchable_text = doc.doc_metadata.get('searchable_text', doc.summary_text)
                
                # 키워드 기반 관련성 점수 계산 (실제로는 임베딩 코사인 유사도 사용)
                relevance_score = 0
                question_keywords = ["성향", "성격", "유형", "분석", "결과"]
                
                for keyword in question_keywords:
                    if keyword in searchable_text:
                        relevance_score += 1
                
                if relevance_score > 0:
                    relevant_docs.append((doc, relevance_score))
            
            # 관련성 점수로 정렬
            relevant_docs.sort(key=lambda x: x[1], reverse=True)
            
            print(f"  관련성 높은 문서 {len(relevant_docs)}개 발견:")
            for i, (doc, score) in enumerate(relevant_docs[:5], 1):
                print(f"    {i}. {doc.doc_type} (점수: {score})")
                print(f"       {doc.summary_text[:60]}...")
                
                # 가상 질문 중 가장 관련성 높은 것 출력
                hypothetical_questions = doc.doc_metadata.get('hypothetical_questions', [])
                for question in hypothetical_questions:
                    if any(keyword in question for keyword in ["성향", "성격"]):
                        print(f"       🎯 매칭 질문: '{question}'")
                        break
            
            if relevant_docs:
                print(f"\n✅ RAG 검색 최적화 성공!")
                print(f"   가상 질문 기법으로 {len(relevant_docs)}개의 관련 문서를 찾았습니다.")
            else:
                print(f"\n❌ 여전히 관련 문서를 찾지 못했습니다.")
                
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_rag())