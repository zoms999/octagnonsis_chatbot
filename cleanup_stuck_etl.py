#!/usr/bin/env python3
"""
중단된 ETL 작업 정리 스크립트
"""

import asyncio
import sys
sys.path.append('.')

from database.connection import db_manager
from sqlalchemy import select, update
from database.models import ChatETLJob
from datetime import datetime, timedelta

async def cleanup_stuck_etl():
    print("=== 중단된 ETL 작업 정리 ===")
    print(f"정리 시작 시간: {datetime.now()}")
    
    try:
        async with db_manager.get_async_session() as db:
            # 5분 이상 진행 중인 작업을 중단된 것으로 간주
            cutoff_time = datetime.now() - timedelta(minutes=5)
            
            # 중단된 작업 조회
            result = await db.execute(
                select(ChatETLJob)
                .where(
                    ChatETLJob.status.in_(['pending', 'processing_queries', 'in_progress'])
                )
                .where(ChatETLJob.started_at < cutoff_time)
            )
            stuck_jobs = result.scalars().all()
            
            if not stuck_jobs:
                print("정리할 중단된 작업이 없습니다.")
                
                # 최근 작업들도 확인 (2분 이상)
                recent_cutoff = datetime.now() - timedelta(minutes=2)
                result = await db.execute(
                    select(ChatETLJob)
                    .where(
                        ChatETLJob.status.in_(['pending', 'processing_queries', 'in_progress'])
                    )
                    .where(ChatETLJob.started_at < recent_cutoff)
                )
                recent_stuck = result.scalars().all()
                
                if recent_stuck:
                    print(f"\n⚠️  2분 이상 진행 중인 작업 {len(recent_stuck)}개 발견:")
                    for job in recent_stuck:
                        elapsed = datetime.now() - job.started_at
                        print(f"  - Job {job.job_id}: {job.status} - 경과시간: {elapsed}")
                    
                    response = input("\n이 작업들도 정리하시겠습니까? (y/N): ")
                    if response.lower() == 'y':
                        stuck_jobs = recent_stuck
                
            if stuck_jobs:
                print(f"\n중단된 작업 {len(stuck_jobs)}개를 정리합니다:")
                
                for job in stuck_jobs:
                    elapsed = datetime.now() - job.started_at
                    print(f"  - Job {job.job_id}: {job.status} (경과시간: {elapsed})")
                
                # 작업 상태를 failed로 변경
                await db.execute(
                    update(ChatETLJob)
                    .where(ChatETLJob.job_id.in_([job.job_id for job in stuck_jobs]))
                    .values(
                        status='failed',
                        error_message='ETL job stuck and cleaned up by admin',
                        error_type='timeout',
                        failed_stage='query_execution',
                        completed_at=datetime.now()
                    )
                )
                
                await db.commit()
                print(f"✅ {len(stuck_jobs)}개 작업을 failed 상태로 변경했습니다.")
            else:
                print("정리할 작업이 없습니다.")
                
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(cleanup_stuck_etl())