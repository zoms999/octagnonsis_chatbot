#!/usr/bin/env python3
"""
ETL 작업 상태 확인 스크립트
"""

import asyncio
import sys
sys.path.append('.')

from database.connection import db_manager
from sqlalchemy import select, desc
from database.models import ChatETLJob
from datetime import datetime

async def check_etl_status():
    print("=== ETL 작업 상태 확인 ===")
    print(f"확인 시간: {datetime.now()}")
    
    try:
        async with db_manager.get_async_session() as db:
            # 모든 ETL 작업 조회 (최신순)
            result = await db.execute(
                select(ChatETLJob)
                .order_by(desc(ChatETLJob.started_at))
                .limit(10)
            )
            jobs = result.scalars().all()
            
            if not jobs:
                print("ETL 작업이 없습니다.")
                return
            
            print(f"\n최근 ETL 작업 {len(jobs)}개:")
            print("-" * 120)
            print(f"{'Job ID':<40} {'User ID':<40} {'Status':<15} {'Progress':<8} {'Started':<20}")
            print("-" * 120)
            
            for job in jobs:
                started_str = job.started_at.strftime("%Y-%m-%d %H:%M:%S")
                print(f"{str(job.job_id):<40} {str(job.user_id):<40} {job.status:<15} {job.progress_percentage:>3}% {started_str:<20}")
                
                if job.current_step:
                    print(f"  현재 단계: {job.current_step}")
                if job.error_message:
                    print(f"  에러: {job.error_message[:100]}...")
                print()
            
            # 진행 중인 작업 확인
            processing_jobs = [job for job in jobs if job.status in ['pending', 'processing_queries', 'in_progress']]
            
            if processing_jobs:
                print(f"\n⚠️  현재 진행 중인 작업 {len(processing_jobs)}개:")
                for job in processing_jobs:
                    elapsed = datetime.now() - job.started_at
                    print(f"  - Job {job.job_id}: {job.status} ({job.progress_percentage}%) - 경과시간: {elapsed}")
                    
                    # 너무 오래 걸리는 작업 확인
                    if elapsed.total_seconds() > 300:  # 5분 이상
                        print(f"    ⚠️  이 작업이 {elapsed}동안 진행 중입니다. 중단된 것일 수 있습니다.")
            else:
                print("\n✅ 현재 진행 중인 ETL 작업이 없습니다.")
                
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_etl_status())