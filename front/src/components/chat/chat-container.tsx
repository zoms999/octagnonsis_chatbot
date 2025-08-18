'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useWebSocketChat } from '@/hooks/websocket-hooks';
import { useAuth } from '@/providers/auth-provider';
import { useDocumentPanel } from '@/hooks/use-document-panel';
import { ChatMessageList } from './chat-message-list';
import { ChatInput } from './chat-input';
import { EmptyState } from './empty-state';
import { ProcessingStatus } from './processing-status';
import { DocumentReferencePanel } from './document-reference-panel';
import { ChatMessage } from '@/lib/types';
import { cn } from '@/lib/utils';

interface ChatContainerProps {
  conversationId?: string;
  userHasDocuments?: boolean;
  onUploadDocuments?: () => void;
  onViewProfile?: () => void;
  showDocumentPanel?: boolean;
  className?: string;
}

export function ChatContainer({
  conversationId,
  userHasDocuments = true,
  onUploadDocuments,
  onViewProfile,
  showDocumentPanel = true,
  className
}: ChatContainerProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  
  // Debug user state
  useEffect(() => {
    console.log('ChatContainer auth state:', {
      user,
      isAuthenticated,
      isLoading,
      userId: user?.id,
      userName: user?.name
    });
  }, [user, isAuthenticated, isLoading]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState(conversationId);
  const [typingStatus, setTypingStatus] = useState<'processing' | 'generating' | 'complete'>('processing');
  
  // Document panel management
  const documentPanel = useDocumentPanel({
    initialCollapsed: false,
    autoCollapseOnMobile: true,
  });

  const {
    sendQuestion,
    isProcessing,
    lastResponse,
    lastError,
    connectionState,
    isConnected,
    rateLimitStatus,
    usedFallback,
    fallbackStatus
  } = useWebSocketChat(
    {
      maxMessages: 10,
      windowMs: 60000, // 1 minute
    },
    {
      maxRetries: 3,
      retryDelay: 1000,
      timeout: 5000,
    }
  );

  // Handle new responses
  useEffect(() => {
    console.log('ChatContainer: lastResponse changed:', lastResponse);
    if (lastResponse) {
      console.log('ChatContainer: Processing new response:', {
        response: lastResponse.response?.substring(0, 100) + '...',
        conversationId: lastResponse.conversation_id,
        retrievedDocs: lastResponse.retrieved_documents?.length
      });

      const responseMessage: ChatMessage = {
        id: `response-${Date.now()}`,
        type: 'assistant',
        content: lastResponse.response,
        timestamp: new Date(),
        confidence_score: lastResponse.confidence_score,
        processing_time: lastResponse.processing_time,
        retrieved_documents: lastResponse.retrieved_documents,
        conversation_id: lastResponse.conversation_id,
      };

      console.log('ChatContainer: Adding response message to list:', responseMessage);
      setMessages(prev => {
        const newMessages = [...prev, responseMessage];
        console.log('ChatContainer: New messages array length:', newMessages.length);
        return newMessages;
      });
      setCurrentConversationId(lastResponse.conversation_id);
      
      // Update document panel with retrieved documents
      if (lastResponse.retrieved_documents && showDocumentPanel) {
        console.log('ChatContainer: Updating document panel with', lastResponse.retrieved_documents.length, 'documents');
        documentPanel.updateDocuments(lastResponse.retrieved_documents);
      }
    }
  }, [lastResponse, showDocumentPanel, documentPanel]);

  // Handle errors
  useEffect(() => {
    if (lastError) {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        type: 'assistant',
        content: `죄송합니다. 오류가 발생했습니다: ${lastError}`,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    }
  }, [lastError]);

  // Update typing status based on processing state
  useEffect(() => {
    if (isProcessing) {
      // Simulate different processing stages
      setTypingStatus('processing');
      
      const timer1 = setTimeout(() => {
        if (isProcessing) setTypingStatus('generating');
      }, 2000);

      return () => {
        clearTimeout(timer1);
      };
    }
  }, [isProcessing]);

  const handleSendMessage = useCallback(async (message: string) => {
    // Get user ID from either id or user_id field (for backward compatibility)
    const userId = user?.id || (user as any)?.user_id;
    
    console.log('handleSendMessage called with:', {
      message: message.substring(0, 50) + '...',
      userId,
      userHasDocuments,
      currentConversationId,
      userObject: user
    });

    if (!userId || !userHasDocuments) {
      console.log('Blocking message send:', { hasUserId: !!userId, userHasDocuments });
      return;
    }

    // Add user message to the list
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: message,
      timestamp: new Date(),
      conversation_id: currentConversationId,
    };

    console.log('Adding user message to list:', userMessage);
    setMessages(prev => [...prev, userMessage]);

    // Send via WebSocket
    try {
      console.log('Calling sendQuestion with userId:', userId);
      await sendQuestion(message, currentConversationId);
      console.log('sendQuestion completed');
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }, [user, userHasDocuments, currentConversationId, sendQuestion]);

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
    <div className={cn('flex h-full bg-white', className)} data-testid="chat-container">
      {/* Main chat area */}
      <div className={cn(
        'flex flex-col flex-1',
        showDocumentPanel && documentPanel.hasDocuments && !documentPanel.isCollapsed && 'mr-80'
      )}>
        {/* Connection status indicator */}
        {!isConnected && (
          <div className={cn(
            "p-3 border-b",
            usedFallback ? "bg-blue-50 border-blue-200" : "bg-yellow-50 border-yellow-200"
          )} data-testid="connection-status">
            <div className={cn(
              "flex items-center gap-2",
              usedFallback ? "text-blue-800" : "text-yellow-800"
            )}>
              <div className={cn(
                "w-2 h-2 rounded-full",
                usedFallback ? "bg-blue-500" : "bg-yellow-500 animate-pulse"
              )} />
              <span className="text-sm">
                {connectionState.status === 'connecting' 
                  ? '재연결 중...' 
                  : usedFallback 
                    ? 'HTTP 모드로 연결됨' 
                    : '연결 끊김'
                }
              </span>
            </div>
          </div>
        )}
        
        {/* Connected status indicator */}
        {isConnected && (
          <div className="hidden" data-testid="connection-status">Connected</div>
        )}

        {/* Processing status */}
        {isProcessing && (
          <div className="p-3 border-b" data-testid="typing-indicator">
            <ProcessingStatus
              status={typingStatus}
              currentStep={
                typingStatus === 'processing' 
                  ? '질문을 분석하고 관련 문서를 검색하고 있습니다...'
                  : '검색된 정보를 바탕으로 답변을 생성하고 있습니다...'
              }
            />
          </div>
        )}

        {/* Messages area */}
        {messages.length === 0 && !isProcessing ? (
          <EmptyState
            userHasDocuments={true}
            className="flex-1"
          />
        ) : (
          <ChatMessageList
            messages={messages}
            isTyping={isProcessing}
            typingStatus={typingStatus}
            className="flex-1"
          />
        )}

        {/* Input area */}
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={false} // Always enable input - fallback will handle disconnected state
          isProcessing={isProcessing}
          rateLimitStatus={rateLimitStatus}
          placeholder={
            !isConnected && usedFallback
              ? '적성 분석에 대해 궁금한 것을 물어보세요... (HTTP 모드)'
              : !isConnected
              ? '연결을 기다리는 중...'
              : '적성 분석에 대해 궁금한 것을 물어보세요...'
          }
        />

        {/* Fallback indicator */}
        {usedFallback && !isConnected && (
          <div className="px-4 py-2 bg-blue-50 border-t border-blue-200" data-testid="fallback-mode">
            <div className="text-xs text-blue-600 text-center">
              현재 HTTP 모드로 동작 중입니다. 채팅 기능은 정상적으로 사용 가능합니다.
            </div>
          </div>
        )}
      </div>

      {/* Document Reference Panel */}
      {showDocumentPanel && (
        <DocumentReferencePanel
          documents={documentPanel.documents}
          isCollapsed={documentPanel.isCollapsed}
          onToggle={documentPanel.toggleCollapsed}
          className={cn(
            'fixed right-0 top-0 h-full z-30 lg:relative lg:top-0',
            documentPanel.isMobile && !documentPanel.isCollapsed && 'shadow-lg'
          )}
        />
      )}

      {/* Mobile backdrop for document panel */}
      {showDocumentPanel && documentPanel.isMobile && !documentPanel.isCollapsed && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={documentPanel.toggleCollapsed}
          aria-hidden="true"
        />
      )}
    </div>
  );
}