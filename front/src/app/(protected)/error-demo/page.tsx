'use client';

import React, { useState } from 'react';
import { ChatErrorDisplay, ChatErrorToast } from '@/components/chat/chat-error-display';
import { ChatErrorHandler } from '@/lib/chat-error-handler';
import { useChatErrorHandler } from '@/hooks/use-chat-error-handler';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

/**
 * Demo page for testing error handling functionality
 * This page demonstrates all error types and recovery actions
 */
export default function ErrorDemoPage() {
  const [showToast, setShowToast] = useState(false);
  const [currentDemoError, setCurrentDemoError] = useState<any>(null);
  
  const errorHandler = useChatErrorHandler({
    autoShow: false, // Manual control for demo
    onError: (error) => {
      console.log('Demo error handled:', error);
    },
    onRetry: () => {
      console.log('Demo retry triggered');
      alert('재시도가 실행되었습니다!');
    }
  });

  // Create different types of errors for demonstration
  const createNetworkError = () => {
    const error = new Error('Failed to fetch');
    error.name = 'TypeError';
    return ChatErrorHandler.processError(error, {
      endpoint: '/api/chat/question',
      userId: 'demo-user'
    });
  };

  const createAuthError = () => {
    const error = {
      status: 401,
      message: 'Unauthorized',
      type: 'auth_error'
    };
    return ChatErrorHandler.processError(error, {
      endpoint: '/api/chat/question',
      userId: 'demo-user'
    });
  };

  const createValidationError = () => {
    const error = {
      status: 400,
      message: 'Invalid input',
      type: 'validation_error',
      field_errors: {
        question: 'Question cannot be empty',
        user_id: 'User ID is required'
      }
    };
    return ChatErrorHandler.processError(error, {
      endpoint: '/api/chat/question',
      question: '',
      userId: 'demo-user'
    });
  };

  const createServerError = () => {
    const error = {
      status: 500,
      message: 'Internal Server Error',
      type: 'server_error'
    };
    return ChatErrorHandler.processError(error, {
      endpoint: '/api/chat/question',
      userId: 'demo-user'
    });
  };

  const createTimeoutError = () => {
    const error = new Error('Request timed out');
    error.name = 'AbortError';
    return ChatErrorHandler.processError(error, {
      endpoint: '/api/chat/question',
      userId: 'demo-user'
    });
  };

  const createUnknownError = () => {
    const error = new Error('Something went wrong');
    return ChatErrorHandler.processError(error, {
      endpoint: '/api/chat/question',
      userId: 'demo-user'
    });
  };

  const showErrorDemo = (errorCreator: () => any) => {
    const error = errorCreator();
    setCurrentDemoError(error);
    errorHandler.handleError(error);
  };

  const showToastDemo = (errorCreator: () => any) => {
    const error = errorCreator();
    setCurrentDemoError(error);
    setShowToast(true);
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4">채팅 에러 핸들링 데모</h1>
        <p className="text-gray-600">
          다양한 에러 타입과 사용자 피드백 시스템을 테스트해볼 수 있습니다.
        </p>
      </div>

      {/* Error Statistics */}
      <Card className="mb-6 p-4">
        <h2 className="text-xl font-semibold mb-3">에러 통계</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="font-medium">총 에러 수</div>
            <div className="text-2xl font-bold text-red-600">
              {errorHandler.errorHistory.length}
            </div>
          </div>
          <div>
            <div className="font-medium">현재 에러</div>
            <div className="text-lg">
              {errorHandler.currentError ? '있음' : '없음'}
            </div>
          </div>
          <div>
            <div className="font-medium">에러 표시 중</div>
            <div className="text-lg">
              {errorHandler.isShowingError ? '예' : '아니오'}
            </div>
          </div>
          <div>
            <div className="font-medium">에러 카운트</div>
            <div className="text-2xl font-bold text-blue-600">
              {errorHandler.errorCount}
            </div>
          </div>
        </div>
      </Card>

      {/* Error Type Demos */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <Card className="p-4">
          <h2 className="text-xl font-semibold mb-4">에러 타입 데모</h2>
          <div className="space-y-2">
            <Button 
              onClick={() => showErrorDemo(createNetworkError)}
              variant="outline"
              className="w-full justify-start"
            >
              네트워크 에러
            </Button>
            <Button 
              onClick={() => showErrorDemo(createAuthError)}
              variant="outline"
              className="w-full justify-start"
            >
              인증 에러
            </Button>
            <Button 
              onClick={() => showErrorDemo(createValidationError)}
              variant="outline"
              className="w-full justify-start"
            >
              유효성 검사 에러
            </Button>
            <Button 
              onClick={() => showErrorDemo(createServerError)}
              variant="outline"
              className="w-full justify-start"
            >
              서버 에러
            </Button>
            <Button 
              onClick={() => showErrorDemo(createTimeoutError)}
              variant="outline"
              className="w-full justify-start"
            >
              타임아웃 에러
            </Button>
            <Button 
              onClick={() => showErrorDemo(createUnknownError)}
              variant="outline"
              className="w-full justify-start"
            >
              알 수 없는 에러
            </Button>
          </div>
        </Card>

        <Card className="p-4">
          <h2 className="text-xl font-semibold mb-4">토스트 알림 데모</h2>
          <div className="space-y-2">
            <Button 
              onClick={() => showToastDemo(createNetworkError)}
              variant="outline"
              className="w-full justify-start"
            >
              네트워크 에러 토스트
            </Button>
            <Button 
              onClick={() => showToastDemo(createAuthError)}
              variant="outline"
              className="w-full justify-start"
            >
              인증 에러 토스트
            </Button>
            <Button 
              onClick={() => showToastDemo(createServerError)}
              variant="outline"
              className="w-full justify-start"
            >
              서버 에러 토스트
            </Button>
          </div>
        </Card>
      </div>

      {/* Error Display Area */}
      {errorHandler.isShowingError && errorHandler.currentError && (
        <Card className="mb-6">
          <div className="p-4">
            <h2 className="text-xl font-semibold mb-4">현재 에러 표시</h2>
            <ChatErrorDisplay
              error={errorHandler.currentError}
              onDismiss={errorHandler.dismissError}
              onRetry={errorHandler.retryLastAction}
            />
          </div>
        </Card>
      )}

      {/* Compact Error Display Demo */}
      {currentDemoError && (
        <Card className="mb-6">
          <div className="p-4">
            <h2 className="text-xl font-semibold mb-4">컴팩트 에러 표시</h2>
            <ChatErrorDisplay
              error={currentDemoError}
              onDismiss={() => setCurrentDemoError(null)}
              onRetry={() => alert('컴팩트 모드에서 재시도!')}
              compact={true}
            />
          </div>
        </Card>
      )}

      {/* Control Buttons */}
      <Card className="p-4">
        <h2 className="text-xl font-semibold mb-4">제어</h2>
        <div className="flex gap-2 flex-wrap">
          <Button 
            onClick={errorHandler.clearError}
            variant="outline"
          >
            현재 에러 지우기
          </Button>
          <Button 
            onClick={errorHandler.clearAllErrors}
            variant="outline"
          >
            모든 에러 지우기
          </Button>
          <Button 
            onClick={errorHandler.retryLastAction}
            variant="outline"
          >
            마지막 액션 재시도
          </Button>
          <Button 
            onClick={() => setCurrentDemoError(null)}
            variant="outline"
          >
            데모 에러 지우기
          </Button>
        </div>
      </Card>

      {/* Error History */}
      {errorHandler.errorHistory.length > 0 && (
        <Card className="p-4">
          <h2 className="text-xl font-semibold mb-4">에러 히스토리</h2>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {errorHandler.errorHistory.map((error, index) => (
              <div 
                key={index}
                className="p-3 bg-gray-50 rounded border text-sm"
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="font-medium">{error.type}</span>
                  <span className="text-xs text-gray-500">
                    {error.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                <div className="text-gray-700">{error.message}</div>
                <div className="text-xs text-gray-500 mt-1">
                  복구 가능: {error.recoverable ? '예' : '아니오'} | 
                  액션: {error.actionRequired || '없음'}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Toast Demo */}
      {showToast && currentDemoError && (
        <ChatErrorToast
          error={currentDemoError}
          onDismiss={() => setShowToast(false)}
          autoHide={true}
          hideDelay={5000}
        />
      )}
    </div>
  );
}