'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSimpleChat } from '@/hooks/use-simple-chat';
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
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState(conversationId);
  const [typingStatus, setTypingStatus] = useState<'processing' | 'generating' | 'complete'>('processing');
  const [processedResponseIds, setProcessedResponseIds] = useState<Set<string>>(new Set());
  const [isProcessingMessage, setIsProcessingMessage] = useState(false);
  
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
    isReady
  } = useSimpleChat({
    enableDebugLogging: true,
    timeout: 30000,
    maxRetries: 2,
    retryDelay: 1000,
    autoResetError: true,
    errorResetDelay: 5000
  });

  // Handle new messages from simplified chat handler
  useEffect(() => {
    console.log('ChatContainer: lastMessage changed:', lastMessage);
    if (lastMessage) {
      // Create unique message ID for deduplication
      const messageId = `${lastMessage.conversation_id}-${lastMessage.content?.substring(0, 50)}-${lastMessage.processing_time}`;
      
      // Check if we've already processed this message
      if (processedResponseIds.has(messageId)) {
        console.log('ChatContainer: Duplicate message detected, skipping:', messageId);
        return;
      }

      console.log('ChatContainer: Processing new message:', {
        messageId,
        content: lastMessage.content?.substring(0, 100) + '...',
        conversationId: lastMessage.conversation_id,
        retrievedDocs: lastMessage.retrieved_documents?.length
      });

      // Mark message as processed
      setProcessedResponseIds(prev => new Set([...prev, messageId]));

      console.log('ChatContainer: Adding message to list:', lastMessage);
      setMessages(prev => {
        // Additional check to prevent duplicate messages
        const isDuplicate = prev.some(msg => 
          msg.type === lastMessage.type && 
          msg.content === lastMessage.content &&
          msg.conversation_id === lastMessage.conversation_id
        );
        
        if (isDuplicate) {
          console.log('ChatContainer: Duplicate message content detected, skipping');
          return prev;
        }
        
        const newMessages = [...prev, lastMessage];
        console.log('ChatContainer: New messages array length:', newMessages.length);
        return newMessages;
      });
      
      if (lastMessage.conversation_id) {
        setCurrentConversationId(lastMessage.conversation_id);
      }
      setIsProcessingMessage(false);
      
      // Update document panel with retrieved documents
      if (lastMessage.retrieved_documents && showDocumentPanel) {
        console.log('ChatContainer: Updating document panel with', lastMessage.retrieved_documents.length, 'documents');
        documentPanel.updateDocuments(lastMessage.retrieved_documents);
      }
    }
  }, [lastMessage, showDocumentPanel, documentPanel, processedResponseIds]);

  // Handle errors with auto-debug
  useEffect(() => {
    if (lastError) {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        type: 'assistant',
        content: `죄송합니다. 오류가 발생했습니다: ${lastError}`,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
      
      // Auto-debug on error in development mode
      if (process.env.NODE_ENV === 'development') {
        autoDebugOnError(user, lastError);
      }
    }
  }, [lastError, user]);

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

    // Add user message to the list
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'user',
      content: message,
      timestamp: new Date(),
      conversation_id: currentConversationId,
    };

    console.log('Adding user message to list:', userMessage);
    setMessages(prev => [...prev, userMessage]);

    // Send via simplified HTTP handler
    try {
      console.log('Calling simplified sendQuestion');
      await sendQuestion(message, currentConversationId);
      console.log('Simplified sendQuestion completed');
    } catch (error) {
      console.error('Failed to send message:', error);
      setIsProcessingMessage(false); // Reset on error
    }
  }, [user, userHasDocuments, currentConversationId, sendQuestion, isProcessingMessage, isProcessing, isReady]);

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
          disabled={!isReady}
          isProcessing={isProcessing}
          rateLimitStatus={undefined} // Simplified - no rate limiting for now
          placeholder={
            !isReady
              ? '로그인이 필요하거나 시스템이 준비 중입니다...'
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