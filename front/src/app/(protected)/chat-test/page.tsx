'use client';

import React from 'react';
import { ChatContainer } from '@/components/chat/chat-container';
import { SimpleChatContainer } from '@/components/chat/simple-chat-container';
import { SafeChatContainer } from '@/components/chat/safe-chat-container';
import { useAuth } from '@/providers/auth-provider';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

/**
 * Simple test page for chat functionality
 */
export default function ChatTestPage() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-4">채팅 기능 테스트</h1>
        <p className="text-gray-600">
          채팅 기능이 제대로 작동하는지 테스트하는 페이지입니다.
        </p>
      </div>

      {/* Auth Status */}
      <Card className="mb-6 p-4">
        <h2 className="text-xl font-semibold mb-3">인증 상태</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="font-medium">로그인 상태</div>
            <div className={`text-lg ${isAuthenticated ? 'text-green-600' : 'text-red-600'}`}>
              {isAuthenticated ? '로그인됨' : '로그인 안됨'}
            </div>
          </div>
          <div>
            <div className="font-medium">로딩 상태</div>
            <div className={`text-lg ${isLoading ? 'text-yellow-600' : 'text-green-600'}`}>
              {isLoading ? '로딩 중' : '완료'}
            </div>
          </div>
          <div>
            <div className="font-medium">사용자 정보</div>
            <div className={`text-lg ${user ? 'text-green-600' : 'text-red-600'}`}>
              {user ? '있음' : '없음'}
            </div>
          </div>
          <div>
            <div className="font-medium">사용자 이름</div>
            <div className="text-lg">
              {user?.name || '없음'}
            </div>
          </div>
        </div>
        
        {user && (
          <div className="mt-4">
            <h3 className="font-medium mb-2">사용자 객체</h3>
            <pre className="text-xs bg-gray-100 p-3 rounded overflow-auto max-h-32">
              {JSON.stringify(user, null, 2)}
            </pre>
          </div>
        )}

        <div className="mt-4">
          <Button onClick={logout} variant="outline" size="sm">
            로그아웃
          </Button>
        </div>
      </Card>

      {/* Chat Container - Original */}
      <Card className="h-[600px] overflow-hidden mb-6">
        <div className="p-4 border-b">
          <h3 className="font-semibold">원본 채팅 컨테이너</h3>
        </div>
        <div className="h-[calc(100%-60px)]">
          <ChatContainer
            userHasDocuments={true}
            showDocumentPanel={false}
            debugMode={true}
            className="h-full"
          />
        </div>
      </Card>

      {/* Chat Container - Simplified */}
      <Card className="h-[600px] overflow-hidden mb-6">
        <div className="p-4 border-b">
          <h3 className="font-semibold">간단한 채팅 컨테이너</h3>
        </div>
        <div className="h-[calc(100%-60px)]">
          <SimpleChatContainer className="h-full" />
        </div>
      </Card>

      {/* Chat Container - Safe */}
      <Card className="h-[600px] overflow-hidden">
        <div className="p-4 border-b">
          <h3 className="font-semibold">안전한 채팅 컨테이너 (권장)</h3>
        </div>
        <div className="h-[calc(100%-60px)]">
          <SafeChatContainer 
            className="h-full"
            userHasDocuments={true}
          />
        </div>
      </Card>

      {/* Instructions */}
      <Card className="mt-6 p-4">
        <h2 className="text-xl font-semibold mb-3">테스트 방법</h2>
        <ol className="list-decimal list-inside space-y-2 text-sm">
          <li>위의 인증 상태가 모두 정상인지 확인하세요.</li>
          <li>채팅 입력창이 활성화되어 있는지 확인하세요.</li>
          <li>간단한 메시지를 입력하고 전송해보세요.</li>
          <li>에러가 발생하면 디버그 정보를 확인하세요.</li>
          <li>개발자 도구의 콘솔에서 로그를 확인하세요.</li>
        </ol>
      </Card>
    </div>
  );
}