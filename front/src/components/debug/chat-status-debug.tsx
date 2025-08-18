'use client';

import React from 'react';
import { useAuth } from '@/providers/auth-provider';
import { extractUserId, getUserIdDebugInfo } from '@/lib/user-utils';
import { Card } from '@/components/ui/card';

interface ChatStatusDebugProps {
  isReady?: boolean;
  isProcessing?: boolean;
  lastError?: string | null;
  currentError?: any;
  isShowingError?: boolean;
}

/**
 * Debug component to show chat status and identify why chat might be disabled
 */
export function ChatStatusDebug({
  isReady = false,
  isProcessing = false,
  lastError = null,
  currentError = null,
  isShowingError = false
}: ChatStatusDebugProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const userId = extractUserId(user);
  const userIdDebug = getUserIdDebugInfo(user);

  return (
    <Card className="p-4 m-4 bg-blue-50 border-blue-200">
      <h3 className="font-semibold text-blue-800 mb-3">채팅 상태 디버그</h3>
      
      <div className="space-y-2 text-sm">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <h4 className="font-medium text-blue-700">인증 상태</h4>
            <ul className="space-y-1 text-xs">
              <li>로그인됨: <span className={isAuthenticated ? 'text-green-600' : 'text-red-600'}>{isAuthenticated ? '예' : '아니오'}</span></li>
              <li>로딩 중: <span className={isLoading ? 'text-yellow-600' : 'text-green-600'}>{isLoading ? '예' : '아니오'}</span></li>
              <li>사용자 객체: <span className={user ? 'text-green-600' : 'text-red-600'}>{user ? '있음' : '없음'}</span></li>
              <li>사용자 ID: <span className={userId ? 'text-green-600' : 'text-red-600'}>{userId || '없음'}</span></li>
              <li>ID 소스: <span className="text-gray-600">{userIdDebug.source}</span></li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-medium text-blue-700">채팅 상태</h4>
            <ul className="space-y-1 text-xs">
              <li>준비됨: <span className={isReady ? 'text-green-600' : 'text-red-600'}>{isReady ? '예' : '아니오'}</span></li>
              <li>처리 중: <span className={isProcessing ? 'text-yellow-600' : 'text-green-600'}>{isProcessing ? '예' : '아니오'}</span></li>
              <li>마지막 에러: <span className={lastError ? 'text-red-600' : 'text-green-600'}>{lastError || '없음'}</span></li>
              <li>현재 에러: <span className={currentError ? 'text-red-600' : 'text-green-600'}>{currentError ? '있음' : '없음'}</span></li>
              <li>에러 표시 중: <span className={isShowingError ? 'text-yellow-600' : 'text-green-600'}>{isShowingError ? '예' : '아니오'}</span></li>
            </ul>
          </div>
        </div>

        {user && (
          <div>
            <h4 className="font-medium text-blue-700 mt-3">사용자 정보</h4>
            <pre className="text-xs bg-white p-2 rounded border overflow-auto max-h-32">
              {JSON.stringify(user, null, 2)}
            </pre>
          </div>
        )}

        {(lastError || currentError) && (
          <div>
            <h4 className="font-medium text-red-700 mt-3">에러 정보</h4>
            <div className="text-xs bg-red-50 p-2 rounded border">
              {lastError && <div><strong>마지막 에러:</strong> {lastError}</div>}
              {currentError && (
                <div>
                  <strong>현재 에러:</strong>
                  <pre className="mt-1 overflow-auto max-h-20">
                    {JSON.stringify(currentError, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="mt-3 p-2 bg-white rounded border">
          <h4 className="font-medium text-blue-700">진단</h4>
          <div className="text-xs mt-1">
            {!isAuthenticated && <div className="text-red-600">❌ 사용자가 로그인되지 않았습니다.</div>}
            {!user && <div className="text-red-600">❌ 사용자 객체가 없습니다.</div>}
            {!userId && <div className="text-red-600">❌ 사용자 ID를 추출할 수 없습니다.</div>}
            {isProcessing && <div className="text-yellow-600">⏳ 메시지를 처리 중입니다.</div>}
            {lastError && <div className="text-red-600">❌ 에러가 발생했습니다: {lastError}</div>}
            {isReady && <div className="text-green-600">✅ 채팅이 준비되었습니다!</div>}
          </div>
        </div>
      </div>
    </Card>
  );
}