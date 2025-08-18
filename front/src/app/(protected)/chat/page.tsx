'use client';

import { Suspense } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { SimpleLayout } from '@/components/layout';
import { LazyChatComponents } from '@/components/lazy';
import { LoadingFallbacks } from '@/lib/lazy-loading';

const { ChatContainer } = LazyChatComponents;

export default function ChatPage() {
  const { user } = useAuth();

  return (
    <SimpleLayout>
      <div className="h-full flex flex-col">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">AI 적성 분석 챗봇</h1>
          <p className="text-muted-foreground mt-1">
            안녕하세요, {user?.name || 'User'}님! 적성 분석에 대해 궁금한 것을 물어보세요.
          </p>
        </div>

        <div className="flex-1 bg-card rounded-lg border overflow-hidden">
          <Suspense fallback={<LoadingFallbacks.ChatPage />}>
            <ChatContainer
              userHasDocuments={true}
              showDocumentPanel={true}
              className="h-full"
            />
          </Suspense>
        </div>
      </div>
    </SimpleLayout>
  );
}