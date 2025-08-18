'use client';

import * as React from 'react';
import { useConversationDetail } from '@/hooks/api-hooks';
import { Modal } from '@/components/ui/modal';
import { Button } from '@/components/ui/button';
import { SkeletonChatMessage } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/toast';
import { Conversation, ConversationDetail, ChatMessage } from '@/lib/types';
import { formatDistanceToNow, format } from 'date-fns';
import { ko } from 'date-fns/locale';

interface ConversationDetailModalProps {
  conversation: Conversation | null;
  isOpen: boolean;
  onClose: () => void;
  onNavigateToConversation?: (conversationId: string) => void;
  className?: string;
}

export function ConversationDetailModal({
  conversation,
  isOpen,
  onClose,
  onNavigateToConversation,
  className,
}: ConversationDetailModalProps) {
  const { toast } = useToast();
  const modalRef = React.useRef<HTMLDivElement>(null);

  const {
    data: conversationDetail,
    isLoading,
    isError,
    error,
    refetch,
  } = useConversationDetail(
    conversation?.conversation_id || ''
  );

  // Handle error state
  React.useEffect(() => {
    if (isError && error) {
      toast.error(
        '대화 상세 정보 로딩 실패',
        '대화 상세 정보를 불러오는 중 오류가 발생했습니다.'
      );
    }
  }, [isError, error, toast]);

  // Focus management for accessibility
  React.useEffect(() => {
    if (isOpen && modalRef.current) {
      const focusableElements = modalRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0] as HTMLElement;
      if (firstElement) {
        firstElement.focus();
      }
    }
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  const handleRetry = () => {
    refetch();
  };

  const handleNavigateToChat = () => {
    if (conversation) {
      // Navigate to chat with this conversation
      window.location.href = `/chat?conversation=${conversation.conversation_id}`;
    }
  };

  if (!conversation) {
    return null;
  }

  const createdAt = new Date(conversation.created_at);
  const updatedAt = new Date(conversation.updated_at);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={conversation.title || `대화 ${conversation.conversation_id.slice(-8)}`}
      className={className}
    >
      <div
        ref={modalRef}
        className="flex flex-col h-full max-h-[80vh]"
        onKeyDown={handleKeyDown}
        tabIndex={-1}
      >
        {/* Header */}
        <div className="flex-shrink-0 border-b pb-4 mb-4">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold line-clamp-2">
                {conversation.title || `대화 ${conversation.conversation_id.slice(-8)}`}
              </h2>
              <div className="flex items-center space-x-4 mt-2 text-sm text-muted-foreground">
                <span className="flex items-center space-x-1">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <span>생성: {format(createdAt, 'yyyy년 M월 d일 HH:mm', { locale: ko })}</span>
                </span>
                <span className="flex items-center space-x-1">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>업데이트: {formatDistanceToNow(updatedAt, { addSuffix: true, locale: ko })}</span>
                </span>
                <span className="flex items-center space-x-1">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <span>{conversation.message_count}개 메시지</span>
                </span>
              </div>
            </div>
            <div className="flex items-center space-x-2 ml-4">
              <Button
                variant="outline"
                size="sm"
                onClick={handleNavigateToChat}
                className="flex items-center space-x-1"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span>채팅으로 이동</span>
              </Button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {isLoading && (
            <div className="space-y-4">
              <SkeletonChatMessage />
              <SkeletonChatMessage />
              <SkeletonChatMessage />
            </div>
          )}

          {isError && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="text-center space-y-4">
                <svg 
                  className="h-12 w-12 mx-auto text-muted-foreground" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
                  />
                </svg>
                <div>
                  <h3 className="text-lg font-medium">대화 내용을 불러올 수 없습니다</h3>
                  <p className="text-muted-foreground mt-1">
                    네트워크 연결을 확인하고 다시 시도해주세요.
                  </p>
                </div>
                <Button onClick={handleRetry} variant="outline">
                  다시 시도
                </Button>
              </div>
            </div>
          )}

          {conversationDetail && (
            <div className="h-full overflow-y-auto">
              <ConversationMessages 
                messages={conversationDetail.messages}
                conversationId={conversationDetail.conversation_id}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 border-t pt-4 mt-4">
          <div className="flex items-center justify-end space-x-2">
            <Button variant="outline" onClick={onClose}>
              닫기
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

interface ConversationMessagesProps {
  messages: ChatMessage[];
  conversationId: string;
}

function ConversationMessages({ messages, conversationId }: ConversationMessagesProps) {
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  React.useEffect(() => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="text-center space-y-4">
          <svg 
            className="h-12 w-12 mx-auto text-muted-foreground" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" 
            />
          </svg>
          <div>
            <h3 className="text-lg font-medium">메시지가 없습니다</h3>
            <p className="text-muted-foreground mt-1">
              이 대화에는 아직 메시지가 없습니다.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-4">
      {messages.map((message, index) => (
        <MessageBubble
          key={message.id || `${conversationId}-${index}`}
          message={message}
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}

interface MessageBubbleProps {
  message: ChatMessage;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.type === 'user';
  const timestamp = format(message.timestamp, 'HH:mm', { locale: ko });

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Message bubble */}
        <div
          className={`
            px-4 py-3 rounded-lg text-sm
            ${isUser 
              ? 'bg-primary text-primary-foreground ml-4' 
              : 'bg-muted text-muted-foreground mr-4'
            }
          `}
        >
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
          
          {/* Metadata for assistant messages */}
          {!isUser && (message.confidence_score || message.processing_time || message.retrieved_documents) && (
            <div className="mt-3 pt-3 border-t border-muted-foreground/20 space-y-2">
              {message.confidence_score && (
                <div className="flex items-center space-x-2 text-xs">
                  <span>신뢰도:</span>
                  <div className="flex items-center space-x-1">
                    <div className="w-16 h-1.5 bg-muted-foreground/20 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all ${
                          message.confidence_score >= 0.8 ? 'bg-green-500' :
                          message.confidence_score >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${message.confidence_score * 100}%` }}
                      />
                    </div>
                    <span>{Math.round(message.confidence_score * 100)}%</span>
                  </div>
                </div>
              )}
              
              {message.processing_time && (
                <div className="flex items-center space-x-2 text-xs">
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>처리 시간: {message.processing_time.toFixed(2)}초</span>
                </div>
              )}
              
              {message.retrieved_documents && message.retrieved_documents.length > 0 && (
                <div className="flex items-center space-x-2 text-xs">
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>참조 문서: {message.retrieved_documents.length}개</span>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Timestamp */}
        <div className={`text-xs text-muted-foreground mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {timestamp}
        </div>
      </div>
    </div>
  );
}