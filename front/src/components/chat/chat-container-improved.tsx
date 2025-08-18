'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSimpleChat } from '@/hooks/use-simple-chat-improved';
import { ChatErrorDisplay } from './chat-error-display';
import { useAuth } from '@/providers/auth-provider';
import { useDocumentPanel } from '@/hooks/use-document-panel';
import { ChatMessageList } from './chat-message-list';
import { ChatInput } from './chat-input';
import { EmptyState } from './empty-state';
import { ProcessingStatus } from './processing-status';
import { DocumentReferencePanel } from './document-reference-panel';
import { ChatMessage } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ChatDebugPanel } from '@/components/debug/chat-debug-panel';
import { exposeDebugFunctions, autoDebugOnError } from '@/lib/debug-utils';
import { extractUserId, getUserIdDebugInfo } from '@/lib/user-utils';

interface ChatContainerProps {
  conversationId?: string;
  userHasDocuments?: boolean;
  onUploadDocuments?: () => void;
  onViewProfile?: () => void;
  showDocumentPanel?: boolean;
  className?: string;
  debugMode?: boolean;
}

export function ChatContainer({
  conversationId,
  userHasDocuments = true,
  onUploadDocuments,
  onViewProfile,
  showDocumentPanel = true,
  className,
  debugMode = false
}: ChatContainerProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  
  // Debug user state with enhanced logging
  useEffect(() => {
    const userIdDebug = getUserIdDebugInfo(user);
    
    console.group('🔍 ChatContainer Auth State Debug');
    console.log('📊 Auth Status:', {
      isAuthenticated,
      isLoading,
      hasUser: userIdDebug.hasUser,
    });
    console.log('👤 User Object:', user);
    console.log('🆔 User ID Debug:', userIdDebug);
    console.log('📛 User Name:', user?.name);
    console.log('🏷️ User Type:', user?.type);
    console.groupEnd();
    
    // Expose debug functions in development mode
    if (process.env.NODE_ENV === 'development' && user) {
      exposeDebugFunctions(user);
    }
  }, [user, isAuthenticated, isLoading]);
  
  // Improved state management for better response handling
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState(conversationId);
  const [typingStatus, setTypingStatus] = useState<'processing' | 'generating' | 'complete'>('processing');
  const [isProcessingMessage, setIsProcessingMessage] = useState(false);
  const lastProcessedMessageRef = useRef<string | null>(null);
  const messageIdsRef = useRef<Set<string>>(new Set());
  
  // Document panel management
  const documentPanel = useDocumentPanel({
    initialCollapsed: false,
    autoCollapseOnMobile: true,
  });

  const {
    sendQuestion,
    isProcessing,
    lastMessage,
    lastError,
    clearError,
    isReady,
    currentError,
    isShowingError,
    dismissError,
    retryLastAction
  } = useSimpleChat({
    enableDebugLogging: true,
    timeout: 30000,
    maxRetries: 2,
    retryDelay: 1000,
    autoResetError: true,
    errorResetDelay: 5000
  });

  // Improved message handling with better deduplication
  useEffect(() => {
    console.log('ChatContainer: lastMessage changed:', lastMessage);
    if (!lastMessage) return;

    // Create a reliable message ID for deduplication
    const messageId = lastMessage.id || `${lastMessage.type}-${lastMessage.conversation_id || 'no-conv'}-${lastMessage.timestamp.getTime()}`;
    
    // Check if we've already processed this exact message
    if (lastProcessedMessageRef.current === messageId || messageIdsRef.current.has(messageId)) {
      console.log('ChatContainer: Duplicate message detected, skipping:', messageId);
      return;
    }

    console.log('ChatContainer: Processing new message:', {
      messageId,
      type: lastMessage.type,
      content: lastMessage.content?.substring(0, 100) + '...',
      conversationId: lastMessage.conversation_id,
      retrievedDocs: lastMessage.retrieved_documents?.length
    });

    // Mark this message as processed
    lastProcessedMessageRef.current = messageId;
    messageIdsRef.current.add(messageId);

    // Process the message based on type
    if (lastMessage.type === 'assistant') {
      // This is a response from the API - add it to messages
      setMessages(prev => {
        // Final check to prevent duplicates
        const existingMessage = prev.find(msg => 
          msg.id === lastMessage.id || 
          (msg.type === lastMessage.type && 
           msg.content === lastMessage.content &&
           Math.abs(msg.timestamp.getTime() - lastMessage.timestamp.getTime()) < 2000)
        );
        
        if (existingMessage) {
          console.log('ChatContainer: Message already exists in list, skipping');
          return prev;
        }
        
        const newMessages = [...prev, lastMessage];
        console.log('ChatContainer: Added assistant message. Total messages:', newMessages.length);
        return newMessages;
      });
      
      // Update conversation ID if provided
      if (lastMessage.conversation_id && lastMessage.conversation_id !== currentConversationId) {
        console.log('ChatContainer: Updating conversation ID:', lastMessage.conversation_id);
        setCurrentConversationId(lastMessage.conversation_id);
      }
      
      // Update document panel with retrieved documents
      if (lastMessage.retrieved_documents && showDocumentPanel) {
        console.log('ChatContainer: Updating document panel with', lastMessage.retrieved_documents.length, 'documents');
        documentPanel.updateDocuments(lastMessage.retrieved_documents);
      }
    }
    
    // Reset processing state when we receive any message
    setIsProcessingMessage(false);
  }, [lastMessage, showDocumentPanel, documentPanel, currentConversationId]);

  // Improved error handling - don't add errors as chat messages
  useEffect(() => {
    if (lastError) {
      console.error('ChatContainer: Error occurred:', lastError);
      
      // Reset processing state on error
      setIsProcessingMessage(false);
      
      // Auto-debug on error in development mode
      if (process.env.NODE_ENV === 'development') {
        autoDebugOnError(user, lastError);
      }
      
      // Don't add error messages to chat - let the UI handle error display
    }
  }, [lastError, user]);

  // Update typing status based on processing state
  useEffect(() => {
    if (isProcessing) {
      setTypingStatus('processing');
      
      const timer1 = setTimeout(() => {
        if (isProcessing) setTypingStatus('generating');
      }, 2000);

      return () => {
        clearTimeout(timer1);
      };
    } else {
      setTypingStatus('complete');
    }
  }, [isProcessing]);

  const handleSendMessage = useCallback(async (message: string) => {
    // Prevent sending if already processing a message
    if (isProcessingMessage || isProcessing) {
      console.log('Message send blocked - already processing:', { isProcessingMessage, isProcessing });
      return;
    }

    // Check if system is ready
    if (!isReady) {
      console.log('System not ready for message sending');
      return;
    }

    // Get user ID using standardized extraction
    const userId = extractUserId(user);
    
    console.log('handleSendMessage called with:', {
      message: message.substring(0, 50) + '...',
      userId,
      userHasDocuments,
      currentConversationId,
      userObject: user,
      isReady
    });

    if (!userId || !userHasDocuments) {
      console.log('Blocking message send:', { hasUserId: !!userId, userHasDocuments });
      return;
    }

    // Set processing state to prevent duplicate sends
    setIsProcessingMessage(true);

    // Add user message to the list immediately
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      type: 'user',
      content: message,
      timestamp: new Date(),
      conversation_id: currentConversationId,
    };

    console.log('Adding user message to list:', userMessage);
    
    // Add user message and mark it as processed
    messageIdsRef.current.add(userMessage.id);
    setMessages(prev => [...prev, userMessage]);

    // Clear any previous errors
    if (lastError) {
      clearError();
    }

    // Send via simplified HTTP handler
    try {
      console.log('Calling simplified sendQuestion');
      await sendQuestion(message, currentConversationId);
      console.log('Simplified sendQuestion completed');
    } catch (error) {
      console.error('Failed to send message:', error);
      setIsProcessingMessage(false); // Reset on error
    }
  }, [user, userHasDocuments, currentConversationId, sendQuestion, isProcessingMessage, isProcessing, isReady, lastError, clearError]);

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
        {/* Connection status indicator - simplified for HTTP mode */}
        <div className="hidden" data-testid="connection-status">
          {isReady ? 'Ready' : 'Not Ready'}
        </div>

        {/* Enhanced error display */}
        {isShowingError && currentError && (
          <div className="border-b" data-testid="error-display">
            <ChatErrorDisplay
              error={currentError}
              onDismiss={dismissError}
              onRetry={retryLastAction}
              compact={true}
              className="m-3"
            />
          </div>
        )}
        
        {/* Fallback for legacy error display */}
        {!isShowingError && lastError && (
          <div className="p-3 bg-red-50 border-b border-red-200" data-testid="legacy-error-display">
            <div className="text-sm text-red-600 flex items-center justify-between">
              <span>오류: {lastError}</span>
              <button 
                onClick={clearError}
                className="text-red-400 hover:text-red-600 ml-2"
                aria-label="오류 메시지 닫기"
              >
                ✕
              </button>
            </div>
          </div>
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
          disabled={!isReady || isProcessingMessage}
          isProcessing={isProcessing || isProcessingMessage}
          rateLimitStatus={undefined} // Simplified - no rate limiting for now
          placeholder={
            !isReady
              ? '로그인이 필요하거나 시스템이 준비 중입니다...'
              : isProcessingMessage
              ? '메시지를 처리 중입니다...'
              : '적성 분석에 대해 궁금한 것을 물어보세요...'
          }
        />

        {/* HTTP mode indicator */}
        {isReady && (
          <div className="px-4 py-2 bg-green-50 border-t border-green-200" data-testid="http-mode">
            <div className="text-xs text-green-600 text-center">
              HTTP 모드로 동작 중입니다. 채팅 기능이 정상적으로 사용 가능합니다.
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

      {/* Debug Panel */}
      {debugMode && <ChatDebugPanel enabled={true} />}
    </div>
  );
}