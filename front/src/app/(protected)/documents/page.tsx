'use client';

import { Suspense } from 'react';
import { LazyDocumentComponents } from '@/components/lazy';
import { LoadingFallbacks } from '@/lib/lazy-loading';

const { DocumentsGrid, DocumentReprocessing } = LazyDocumentComponents;

export default function DocumentsPage() {
  return (
    <div className="container mx-auto px-4 py-6 max-w-6xl">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">문서 관리</h1>
          <p className="text-muted-foreground mt-1">
            처리된 문서를 확인하고 관리할 수 있습니다.
          </p>
        </div>

        <Suspense fallback={<LoadingFallbacks.Component />}>
          <DocumentReprocessing />
        </Suspense>
        
        <Suspense fallback={<LoadingFallbacks.Component />}>
          <DocumentsGrid />
        </Suspense>
      </div>
    </div>
  );
}