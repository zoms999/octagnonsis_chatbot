#!/usr/bin/env python3
"""
Test hypothetical questions generation and RAG optimization
"""

import asyncio
import sys
sys.path.append('.')
from etl.legacy_query_executor import LegacyQueryExecutor
from etl.document_transformer import DocumentTransformer
from database.repositories import save_chunked_documents
from database.connection import db_manager

async def test_hypothetical_questions():
    """가상 질문 생성 기능을 테스트합니다."""
    
    user_id = "9b08ed21-fddf-4998-a1f4-29bccda89a54"  # 기존 사용자
    anp_seq = 18223
    
    print(f"가상 질문 생성 테스트 시작:")
    print(f"  User ID: {user_id}")
    print(f"  ANP Seq: {anp_seq}")
    
    try:
        # 1. 쿼리 실행
        executor = LegacyQueryExecutor()
        async with db_manager.get_async_session() as session:
            results = await executor.execute_all_queries_async(session, anp_seq)
            
            successful_results = await executor.get_successful_results(results)
            print(f"✅ 쿼리 실행 완료: {len(successful_results)}개 쿼리")
            
            # 2. 문서 변환 (가상 질문 생성 포함)
            transformer = DocumentTransformer()
            transformed_docs = await transformer.transform_all_documents(successful_results)
            print(f"✅ 문서 변환 완료: {len(transformed_docs)}개 문서")
            
            # 3. 가상 질문 확인
            print("\n📝 생성된 가상 질문 샘플:")
            for i, doc in enumerate(transformed_docs[:3]):  # 처음 3개만 확인
                print(f"\n  문서 {i+1}: {doc.doc_type}")
                print(f"    요약: {doc.summary_text[:50]}...")
                hypothetical_questions = doc.metadata.get('hypothetical_questions', [])
                print(f"    가상 질문들:")
                for j, question in enumerate(hypothetical_questions, 1):
                    print(f"      {j}. {question}")
                searchable_text = doc.metadata.get('searchable_text', '')
                print(f"    검색용 텍스트 길이: {len(searchable_text)} 문자")
            
            # 4. 문서 저장
            await save_chunked_documents(session, user_id, transformed_docs)
            print(f"\n✅ 문서 저장 완료: {len(transformed_docs)}개 문서")
            
            # 5. 저장된 문서 확인
            from database.models import ChatDocument
            from sqlalchemy import select, func
            
            stmt = select(func.count(ChatDocument.doc_id)).where(ChatDocument.user_id == user_id)
            result = await session.execute(stmt)
            doc_count = result.scalar()
            print(f"✅ 데이터베이스 확인: {doc_count}개 문서 저장됨")
            
            # 6. 메타데이터 확인
            stmt = select(ChatDocument).where(ChatDocument.user_id == user_id).limit(3)
            result = await session.execute(stmt)
            sample_docs = result.scalars().all()
            
            print(f"\n🔍 저장된 문서의 메타데이터 샘플:")
            for i, doc in enumerate(sample_docs, 1):
                hypothetical_questions = doc.doc_metadata.get('hypothetical_questions', [])
                print(f"  문서 {i}: {doc.doc_type}")
                print(f"    가상 질문 수: {len(hypothetical_questions)}")
                if hypothetical_questions:
                    print(f"    첫 번째 질문: {hypothetical_questions[0]}")
        
        await executor.close()
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hypothetical_questions())