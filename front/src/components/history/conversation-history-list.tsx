'use client';

import * as React from 'react';
import { useAuth } from '@/providers/auth-provider';
import { useConversationHistory } from '@/hooks/api-hooks';
import { Button } from '@/components/ui/button';
import { SkeletonChatHistory } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/toast';
import { Conversation } from '@/lib/types';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';

interface ConversationHistoryListProps {
  onConversationSelect?: (conversation: Conversation) => void;
  className?: string;
}

export function ConversationHistoryList({ 
  onConversationSelect,
  className 
}: ConversationHistoryListProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [currentPage, setCurrentPage] = React.useState(1);
  const [limit] = React.useState(20);

  const {
    data: historyData,
    isLoading,
    isError,
    error,
    refetch,
  } = useConversationHistory(
    user?.id || '',
    currentPage,
    limit
  );

  // Handle error state
  React.useEffect(() => {
    if (isError && error) {
      toast.error(
        '대화 기록 로딩 실패',
        '대화 기록을 불러오는 중 오류가 발생했습니다.'
      );
    }
  }, [isError, error, toast]);

  const handleConversationClick = (conversation: Conversation) => {
    onConversationSelect?.(conversation);
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
  };

  const handleRetry = () => {
    refetch();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className={className}>
        <SkeletonChatHistory />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className={`${className} flex flex-col items-center justify-center py-12`}>
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
            <h3 className="text-lg font-medium">대화 기록을 불러올 수 없습니다</h3>
            <p className="text-muted-foreground mt-1">
              네트워크 연결을 확인하고 다시 시도해주세요.
            </p>
          </div>
          <Button onClick={handleRetry} variant="outline">
            다시 시도
          </Button>
        </div>
      </div>
    );
  }

  // Empty state
  if (!historyData?.conversations || historyData.conversations.length === 0) {
    return (
      <div className={`${className} flex flex-col items-center justify-center py-12`}>
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
            <h3 className="text-lg font-medium">아직 대화 기록이 없습니다</h3>
            <p className="text-muted-foreground mt-1">
              채팅을 시작하면 대화 기록이 여기에 표시됩니다.
            </p>
          </div>
          <Button 
            onClick={() => window.location.href = '/chat'} 
            variant="default"
          >
            채팅 시작하기
          </Button>
        </div>
      </div>
    );
  }

  const { conversations, total, page } = historyData;
  const totalPages = Math.ceil(total / limit);
  const hasNextPage = page < totalPages;
  const hasPrevPage = page > 1;

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold">대화 기록</h2>
          <p className="text-sm text-muted-foreground">
            총 {total}개의 대화
          </p>
        </div>
      </div>

      {/* Conversation List */}
      <div className="space-y-3">
        {conversations.map((conversation) => (
          <ConversationCard
            key={conversation.conversation_id}
            conversation={conversation}
            onClick={() => handleConversationClick(conversation)}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-8 pt-6 border-t">
          <div className="text-sm text-muted-foreground">
            페이지 {page} / {totalPages}
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(page - 1)}
              disabled={!hasPrevPage}
            >
              이전
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(page + 1)}
              disabled={!hasNextPage}
            >
              다음
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

interface ConversationCardProps {
  conversation: Conversation;
  onClick: () => void;
}

function ConversationCard({ conversation, onClick }: ConversationCardProps) {
  const createdAt = new Date(conversation.created_at);
  const updatedAt = new Date(conversation.updated_at);
  const timeAgo = formatDistanceToNow(updatedAt, { 
    addSuffix: true, 
    locale: ko 
  });

  return (
    <div
      className="border rounded-lg p-4 hover:bg-accent/50 cursor-pointer transition-colors"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* Title or fallback */}
          <h3 className="font-medium text-sm line-clamp-1">
            {conversation.title || `대화 ${conversation.conversation_id.slice(-8)}`}
          </h3>
          
          {/* Last message preview */}
          {conversation.last_message_preview && (
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
              {conversation.last_message_preview}
            </p>
          )}
          
          {/* Metadata */}
          <div className="flex items-center space-x-4 mt-2 text-xs text-muted-foreground">
            <span className="flex items-center space-x-1">
              <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <span>{conversation.message_count}개 메시지</span>
            </span>
            <span className="flex items-center space-x-1">
              <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{timeAgo}</span>
            </span>
          </div>
        </div>
        
        {/* Arrow indicator */}
        <div className="ml-4 flex-shrink-0">
          <svg 
            className="h-4 w-4 text-muted-foreground" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M9 5l7 7-7 7" 
            />
          </svg>
        </div>
      </div>
    </div>
  );
}