'use client';

import { Suspense } from 'react';
import { LazyProfileComponents } from '@/components/lazy';
import { LoadingFallbacks } from '@/lib/lazy-loading';

const { UserProfileCard } = LazyProfileComponents;

export default function ProfilePage() {
  return (
    <div className="container mx-auto px-4 py-6 max-w-4xl">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">프로필</h1>
          <p className="text-muted-foreground mt-1">
            계정 정보와 사용 현황을 확인할 수 있습니다.
          </p>
        </div>

        <Suspense fallback={<LoadingFallbacks.ProfilePage />}>
          <UserProfileCard />
        </Suspense>
      </div>
    </div>
  );
}