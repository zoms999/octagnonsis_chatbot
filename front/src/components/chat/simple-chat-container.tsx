'use client';

import React, { useState, useCallback } from 'react';
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

interface SimpleChatContainerProps {
  className?: string;
}

/**
 * Simplified chat container with direct API calls and minimal state management
 * This version bypasses complex hooks and handlers for debugging purposes
 */
export function SimpleChatContainer({ className }: SimpleChatContainerProps) {
  const { user, isAuthenticated } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentError, setCurrentError] = useState<any>(null);

  // Simple ready check
  const userId = extractUserId(user);
  const isReady = isAuthenticated && !!userId && !isProcessing;

  console.log('SimpleChatContainer render:', {
    isAuthenticated,
    userId,
    isReady,
    isProcessing,
    hasError: !!currentError,
    messageCount: messages.length
  });

  const handleSendMessage = useCallback(async (message: string) => {
    if (!isReady || !userId) {
      console.error('Cannot send message: not ready or no user ID');
      return;
    }

    console.log('SimpleChatContainer: Sending message:', message.substring(0, 50) + '...');

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
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
      
      console.log('SimpleChatContainer: Received response:', {
        hasResponse: !!response.response,
        conversationId: response.conversation_id,
        responseLength: response.response?.length
      });

      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
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
      console.error('SimpleChatContainer: Error sending message:', error);
      
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

  return (
    <div className={cn('flex flex-col h-full bg-white', className)}>
      {/* Debug info in development */}
      {process.env.NODE_ENV === 'development' && (
        <div className="p-2 bg-blue-50 border-b text-xs">
          <div className="flex gap-4">
            <span>인증: {isAuthenticated ? '✅' : '❌'}</span>
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
          !isAuthenticated
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
            채팅이 준비되었습니다. 메시지를 입력해보세요!
          </div>
        </div>
      )}
    </div>
  );
}