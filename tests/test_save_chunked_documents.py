#!/usr/bin/env python3
"""
Test save_chunked_documents function
"""

import asyncio
import sys
import uuid
from typing import List

sys.path.append('.')

from database.repositories import save_chunked_documents
from database.connection import db_manager
from etl.document_transformer import TransformedDocument

async def test_save_chunked_documents():
    """Test the save_chunked_documents function"""
    
    # 테스트용 사용자 ID 생성
    test_user_id = str(uuid.uuid4())
    
    # 테스트용 문서들 생성
    test_documents = [
        TransformedDocument(
            doc_type="PERSONALITY_PROFILE",
            content={
                "primary_tendency": "창의형",
                "secondary_tendency": "협력형",
                "top_tendencies": ["창의형", "협력형", "논리형"]
            },
            summary_text="사용자는 창의적이고 협력적인 성향을 가지고 있습니다.",
            metadata={"chunk_type": "personality_summary", "source": "tendency_analysis"},
            embedding_vector=None  # 임베딩은 나중에 추가됨
        ),
        TransformedDocument(
            doc_type="THINKING_SKILLS",
            content={
                "core_thinking_skills": [
                    {"skill": "창의적 사고", "score": 85},
                    {"skill": "논리적 사고", "score": 78}
                ]
            },
            summary_text="사용자는 창의적 사고와 논리적 사고 능력이 뛰어납니다.",
            metadata={"chunk_type": "thinking_skills_summary", "source": "thinking_analysis"},
            embedding_vector=None
        )
    ]
    
    try:
        async with db_manager.get_async_session() as session:
            print(f"Testing save_chunked_documents with user_id: {test_user_id}")
            print(f"Number of documents to save: {len(test_documents)}")
            
            # 기존 사용자 확인 또는 생성
            from database.models import ChatUser
            from datetime import datetime
            from sqlalchemy import select
            
            # 기존 사용자 확인
            stmt = select(ChatUser).where(ChatUser.anp_seq == 99999)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                test_user_id = str(existing_user.user_id)
                print(f"✅ Using existing test user: {existing_user.name}")
            else:
                # 새 사용자 생성
                test_user = ChatUser(
                    user_id=uuid.UUID(test_user_id),
                    anp_seq=99999,  # 테스트용 anp_seq
                    name=f"Test User {test_user_id[:8]}",
                    email=f"test_{test_user_id[:8]}@example.com",
                    test_completed_at=datetime.utcnow()  # NOT NULL 제약조건 만족
                )
                session.add(test_user)
                await session.commit()
                print(f"✅ Created test user: {test_user.name}")
            
            # 함수 실행
            await save_chunked_documents(session, test_user_id, test_documents)
            
            print("✅ save_chunked_documents executed successfully!")
            
            # 저장된 문서 확인
            from database.repositories import DocumentRepository
            repo = DocumentRepository(session)
            saved_docs = await repo.get_documents_by_user(uuid.UUID(test_user_id))
            
            print(f"✅ Saved {len(saved_docs)} documents successfully")
            for doc in saved_docs:
                print(f"  - {doc.doc_type}: {doc.summary_text[:50]}...")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_save_chunked_documents())