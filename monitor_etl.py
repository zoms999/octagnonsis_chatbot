#!/usr/bin/env python3
"""
Monitor ETL job progress
"""

import asyncio
import sys
sys.path.append('.')
from database.connection import db_manager
from database.models import ChatETLJob, ChatDocument
from sqlalchemy import select, func

async def monitor_etl():
    job_id = 'f5e4ce91-7297-4764-8e26-ad2159cc63d7'
    
    for i in range(6):  # 최대 6번 확인 (약 3분)
        async with db_manager.get_async_session() as session:
            # ETL 작업 상태 확인
            stmt = select(ChatETLJob).where(ChatETLJob.job_id == job_id)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            
            if job:
                print(f'[{i+1}/6] Status: {job.status}, Progress: {job.progress_percentage}%, Step: {job.current_step}')
                
                if job.status in ['completed', 'failed']:
                    print(f'ETL 작업 완료: {job.status}')
                    if job.error_message:
                        print(f'에러 메시지: {job.error_message}')
                    break
                    
                # 문서 수 확인
                user_id = '5294802c-2219-4651-a4a5-a9a5dae7546f'
                stmt = select(func.count(ChatDocument.doc_id)).where(ChatDocument.user_id == user_id)
                result = await session.execute(stmt)
                doc_count = result.scalar()
                print(f'  현재 문서 수: {doc_count}')
            else:
                print(f'[{i+1}/6] 작업을 찾을 수 없습니다.')
                break
        
        if i < 5:  # 마지막이 아니면 대기
            await asyncio.sleep(30)  # 30초 대기

if __name__ == "__main__":
    asyncio.run(monitor_etl())