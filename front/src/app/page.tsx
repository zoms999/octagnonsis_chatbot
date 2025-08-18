'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/providers/auth-provider';
import { Button } from '@/components/ui/button';

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/chat');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="max-w-4xl mx-auto text-center space-y-8">
        <div className="space-y-4">
          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
            AI 적성 분석 챗봇
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            AI와 대화하며 개인 맞춤형 적성 분석을 받아보세요. 
            당신의 강점과 적합한 직업을 발견해보세요.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button 
            size="lg" 
            onClick={() => router.push('/login')}
            className="text-lg px-8 py-3"
          >
            시작하기
          </Button>
          <Button 
            variant="outline" 
            size="lg"
            onClick={() => router.push('/login')}
            className="text-lg px-8 py-3"
          >
            로그인
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16">
          <div className="p-6 rounded-lg border bg-card">
            <h3 className="text-lg font-semibold mb-2">개인 맞춤 분석</h3>
            <p className="text-muted-foreground">
              AI가 당신의 답변을 분석하여 개인에게 최적화된 적성 분석을 제공합니다.
            </p>
          </div>
          
          <div className="p-6 rounded-lg border bg-card">
            <h3 className="text-lg font-semibold mb-2">실시간 대화</h3>
            <p className="text-muted-foreground">
              자연스러운 대화를 통해 편안하게 적성 검사를 진행할 수 있습니다.
            </p>
          </div>
          
          <div className="p-6 rounded-lg border bg-card">
            <h3 className="text-lg font-semibold mb-2">상세한 결과</h3>
            <p className="text-muted-foreground">
              분석 결과와 함께 추천 직업, 학습 방향 등 구체적인 가이드를 제공합니다.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}