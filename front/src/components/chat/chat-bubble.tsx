'use client';

import React from 'react';
import { ChatMessage } from '@/lib/types';
import { cn } from '@/lib/utils';
import { FeedbackButtons } from './feedback-buttons';
import { useFeedback } from '@/hooks/use-feedback';
import { useToast } from '@/components/ui/toast';

interface ChatBubbleProps {
  message: ChatMessage;
  className?: string;
  showFeedback?: boolean;
}

export function ChatBubble({ message, className, showFeedback = true }: ChatBubbleProps) {
  const isUser = message.type === 'user';
  const { toast } = useToast();
  
  const { submitFeedback, hasFeedback, isSubmitting } = useFeedback({
    onSuccess: (response) => {
      toast.success('피드백 제출 완료', '소중한 의견 감사합니다!');
    },
    onError: (error) => {
      console.error('Feedback submission failed:', error);
      toast.error('피드백 제출 실패', '다시 시도해주세요.');
    },
  });
  
  return (
    <div
      className={cn(
        'flex w-full mb-4',
        isUser ? 'justify-end' : 'justify-start',
        className
      )}
      data-testid="chat-message"
      data-sender={isUser ? 'user' : 'assistant'}
    >
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-3 shadow-sm',
          isUser
            ? 'bg-blue-600 text-white ml-12'
            : 'bg-gray-100 text-gray-900 mr-12'
        )}
      >
        <div className="whitespace-pre-wrap break-words">
          {message.content}
        </div>
        
        {/* Assistant message metadata */}
        {!isUser && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <div className="flex flex-wrap gap-4 text-xs text-gray-600">
              {message.confidence_score !== undefined && (
                <div className="flex items-center gap-1" data-testid="confidence-score">
                  <span>신뢰도:</span>
                  <div className="flex items-center gap-1">
                    <div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all',
                          message.confidence_score >= 0.8
                            ? 'bg-green-500'
                            : message.confidence_score >= 0.6
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        )}
                        style={{ width: `${message.confidence_score * 100}%` }}
                      />
                    </div>
                    <span>{Math.round(message.confidence_score * 100)}%</span>
                  </div>
                </div>
              )}
              
              {message.processing_time !== undefined && (
                <div className="flex items-center gap-1" data-testid="processing-time">
                  <span>처리시간:</span>
                  <span>{message.processing_time.toFixed(2)}초</span>
                </div>
              )}
              
              {message.retrieved_documents && message.retrieved_documents.length > 0 && (
                <div className="flex items-center gap-1" data-testid="document-count">
                  <span>참조문서:</span>
                  <span>{message.retrieved_documents.length}개</span>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Feedback buttons for assistant messages */}
        {!isUser && showFeedback && message.conversation_id && !hasFeedback(message.id) && (
          <FeedbackButtons
            messageId={message.id}
            conversationId={message.conversation_id}
            onFeedbackSubmitted={submitFeedback}
            className="border-t border-gray-200 pt-2"
          />
        )}
        
        {/* Feedback submitted indicator */}
        {!isUser && hasFeedback(message.id) && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <div className="flex items-center gap-1 text-xs text-green-600">
              <span>✓</span>
              <span>피드백이 제출되었습니다</span>
            </div>
          </div>
        )}
        
        {/* Timestamp */}
        <div className={cn(
          'mt-2 text-xs',
          isUser ? 'text-blue-200' : 'text-gray-500'
        )}>
          {message.timestamp.toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      </div>
    </div>
  );
}