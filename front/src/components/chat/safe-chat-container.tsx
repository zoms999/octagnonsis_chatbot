'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { ChatInput } from './chat-input';
import { ChatMessageList } from './chat-message-list';
import { EmptyState } from './empty-state';
import { ProcessingStatus } from './processing-status';
import { ChatErrorDisplay } from './chat-error-display';
import { ChatMessage } from '@/lib/types';
import { ApiClient } from '@/lib/api';
import { extractUserId } from '@/lib/user-utils';
import { ChatErrorHandler } from '@/lib/chat-error-handler';
import { cn } from '@/lib/utils';

interface SafeChatContainerProps {
  className?: string;
  userHasDocuments?: boolean;
  onUploadDocuments?: () => void;
  onViewProfile?: () => void;
}

/**
 * Safe chat container with proper initialization order and error handling
 */
export function SafeChatContainer({ 
  className,
  userHasDocuments = true,
  onUploadDocuments,
  onViewProfile
}: SafeChatContainerProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentError, setCurrentError] = useState<any>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize after auth is ready
  useEffect(() => {
    if (!isLoading) {
      setIsInitialized(true);
    }
  }, [isLoading]);

  // Calculate ready state safely
  const userId = extractUserId(user);
  const isReady = isInitialized && isAuthenticated && !!userId && !isProcessing;

  console.log('SafeChatContainer state:', {
    isInitialized,
    isAuthenticated,
    isLoading,
    userId: userId || 'null',
    isReady,
    isProcessing,
    hasError: !!currentError,
    messageCount: messages.length
  });

  const handleSendMessage = useCallback(async (message: string) => {
    if (!isReady || !userId) {
      console.error('SafeChatContainer: Cannot send message - not ready');
      return;
    }

    console.log('SafeChatContainer: Sending message:', message.substring(0, 50) + '...');

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      type: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsProcessing(true);
    setCurrentError(null);

    try {
      // Direct API call
      const response = await ApiClient.sendQuestion(message, undefined, userId);
      
      console.log('SafeChatContainer: Received response:', {
        hasResponse: !!response.response,
        conversationId: response.conversation_id,
        responseLength: response.response?.length
      });

      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        type: 'assistant',
        content: response.response,
        timestamp: new Date(),
        conversation_id: response.conversation_id,
        confidence_score: response.confidence_score,
        processing_time: response.processing_time,
        retrieved_documents: response.retrieved_documents || [],
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error('SafeChatContainer: Error sending message:', error);
      
      // Process error through error handler
      const chatError = ChatErrorHandler.processError(error, {
        userId,
        question: message.substring(0, 100),
        endpoint: '/api/chat/question'
      });
      
      setCurrentError(chatError);
    } finally {
      setIsProcessing(false);
    }
  }, [isReady, userId]);

  const clearError = useCallback(() => {
    setCurrentError(null);
  }, []);

  const retryLastMessage = useCallback(() => {
    // Find the last user message and resend it
    const lastUserMessage = [...messages].reverse().find(msg => msg.type === 'user');
    if (lastUserMessage) {
      handleSendMessage(lastUserMessage.content);
    }
  }, [messages, handleSendMessage]);

  // Show loading state while initializing
  if (!isInitialized || isLoading) {
    return (
      <div className={cn('flex flex-col h-full bg-white items-center justify-center', className)}>
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">시스템을 초기화하고 있습니다...</p>
        </div>
      </div>
    );
  }

  // Show empty state if user has no documents
  if (!userHasDocuments) {
    return (
      <div className={cn('flex flex-col h-full', className)}>
        <EmptyState
          userHasDocuments={false}
          onUploadDocuments={onUploadDocuments}
          onViewProfile={onViewProfile}
          className="flex-1"
        />
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col h-full bg-white', className)}>
      {/* Debug info in development */}
      {process.env.NODE_ENV === 'development' && (
        <div className="p-2 bg-blue-50 border-b text-xs">
          <div className="flex gap-4 flex-wrap">
            <span>초기화: {isInitialized ? '✅' : '❌'}</span>
            <span>인증: {isAuthenticated ? '✅' : '❌'}</span>
            <span>로딩: {isLoading ? '⏳' : '✅'}</span>
            <span>사용자ID: {userId || '❌'}</span>
            <span>준비: {isReady ? '✅' : '❌'}</span>
            <span>처리중: {isProcessing ? '⏳' : '✅'}</span>
            <span>에러: {currentError ? '❌' : '✅'}</span>
          </div>
        </div>
      )}

      {/* Error display */}
      {currentError && (
        <div className="border-b">
          <ChatErrorDisplay
            error={currentError}
            onDismiss={clearError}
            onRetry={retryLastMessage}
            compact={true}
            className="m-3"
          />
        </div>
      )}

      {/* Processing status */}
      {isProcessing && (
        <div className="p-3 border-b">
          <ProcessingStatus
            status="processing"
            currentStep="메시지를 처리하고 있습니다..."
          />
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-hidden">
        {messages.length === 0 && !isProcessing ? (
          <EmptyState
            userHasDocuments={true}
            className="h-full"
          />
        ) : (
          <ChatMessageList
            messages={messages}
            isTyping={isProcessing}
            typingStatus="processing"
            className="h-full"
          />
        )}
      </div>

      {/* Input area */}
      <ChatInput
        onSendMessage={handleSendMessage}
        disabled={!isReady}
        isProcessing={isProcessing}
        rateLimitStatus={{
          canSendMessage: isReady,
          remainingMessages: 100,
          timeUntilNextMessage: 0
        }}
        placeholder={
          !isInitialized
            ? '시스템을 초기화하고 있습니다...'
            : !isAuthenticated
            ? '로그인이 필요합니다...'
            : !userId
            ? '사용자 정보를 불러오는 중...'
            : isProcessing
            ? '메시지를 처리 중입니다...'
            : '적성 분석에 대해 궁금한 것을 물어보세요...'
        }
      />

      {/* Status indicator */}
      {isReady && (
        <div className="px-4 py-2 bg-green-50 border-t border-green-200">
          <div className="text-xs text-green-600 text-center">
            ✅ 채팅이 준비되었습니다. 메시지를 입력해보세요!
          </div>
        </div>
      )}

      {/* Not ready indicator */}
      {!isReady && isInitialized && (
        <div className="px-4 py-2 bg-yellow-50 border-t border-yellow-200">
          <div className="text-xs text-yellow-600 text-center">
            {!isAuthenticated && '🔐 로그인이 필요합니다'}
            {isAuthenticated && !userId && '👤 사용자 정보를 확인하는 중입니다'}
            {isAuthenticated && userId && isProcessing && '⏳ 메시지를 처리하고 있습니다'}
          </div>
        </div>
      )}
    </div>
  );
}