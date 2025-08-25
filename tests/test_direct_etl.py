#!/usr/bin/env python3
"""
Direct ETL test with existing user
"""

import asyncio
import sys
import uuid
sys.path.append('.')
from etl.etl_orchestrator import ETLOrchestrator
from database.connection import db_manager

async def test_direct_etl():
    """실제 데이터가 있는 anp_seq로 ETL 실행"""
    
    user_id = str(uuid.uuid4())  # 새로운 사용자 ID 생성
    anp_seq = 18223  # 실제 데이터가 있는 anp_seq
    
    print(f"직접 ETL 실행 시작:")
    print(f"  User ID: {user_id}")
    print(f"  ANP Seq: {anp_seq}")
    
    try:
        orchestrator = ETLOrchestrator()
        
        # ETL 실행을 위한 필요한 객체들 생성
        from etl.test_completion_handler import JobTracker
        
        job_id = str(uuid.uuid4())
        job_tracker = JobTracker()
        
        async with db_manager.get_async_session() as session:
            result = await orchestrator.process_test_completion(
                user_id=user_id,
                anp_seq=anp_seq,
                job_id=job_id,
                session=session,
                job_tracker=job_tracker
            )
        
        print(f"✅ ETL 완료!")
        print(f"  처리된 쿼리: {result.get('queries_processed', 0)}")
        print(f"  생성된 문서: {result.get('documents_created', 0)}")
        print(f"  처리 시간: {result.get('processing_time', 0):.2f}초")
        
        # 생성된 문서 확인
        from database.models import ChatDocument
        from sqlalchemy import select, func
        
        async with db_manager.get_async_session() as session:
            stmt = select(func.count(ChatDocument.doc_id)).where(ChatDocument.user_id == user_id)
            result = await session.execute(stmt)
            doc_count = result.scalar()
            print(f"  데이터베이스의 문서 수: {doc_count}")
            
            if doc_count > 0:
                # 문서 타입별 개수 확인
                stmt = select(ChatDocument.doc_type, func.count(ChatDocument.doc_id)).where(
                    ChatDocument.user_id == user_id
                ).group_by(ChatDocument.doc_type)
                result = await session.execute(stmt)
                doc_types = result.all()
                
                print("  문서 타입별 개수:")
                for doc_type, count in doc_types:
                    print(f"    {doc_type}: {count}개")
        
    except Exception as e:
        print(f"❌ ETL 실행 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_etl())