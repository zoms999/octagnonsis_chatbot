'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
  isProcessing?: boolean;
  rateLimitStatus?: {
    canSendMessage: boolean;
    remainingMessages: number;
    timeUntilNextMessage: number;
  };
  className?: string;
}

export function ChatInput({
  onSendMessage,
  disabled = false,
  placeholder = '적성 분석에 대해 궁금한 것을 물어보세요...',
  maxLength = 1000,
  isProcessing = false,
  rateLimitStatus,
  className
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    console.log('ChatInput handleSubmit called:', {
      message: message.substring(0, 50) + '...',
      disabled,
      isProcessing,
      canSendMessage: rateLimitStatus?.canSendMessage,
      messageLength: message.trim().length
    });
    
    // Check if we can send message (default to true if no rate limit status)
    const canSendMessage = rateLimitStatus?.canSendMessage ?? true;
    
    if (!message.trim() || disabled || isProcessing || !canSendMessage) {
      console.log('Blocking submit due to conditions:', {
        hasMessage: !!message.trim(),
        disabled,
        isProcessing,
        canSendMessage
      });
      return;
    }

    const messageToSend = message.trim();
    console.log('Calling onSendMessage with:', messageToSend);
    
    // Clear message immediately to prevent double submission
    setMessage('');
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    
    // Send message after clearing input
    onSendMessage(messageToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const canSendMessage = rateLimitStatus?.canSendMessage ?? true;
  const isInputDisabled = disabled || isProcessing || !canSendMessage;
  const remainingChars = maxLength - message.length;

  return (
    <div className={cn('border-t bg-white p-4', className)}>
      {/* Rate limit warning */}
      {rateLimitStatus && !canSendMessage && (
        <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg" data-testid="rate-limit-message">
          <div className="flex items-center gap-2 text-yellow-800">
            <span className="text-sm">⏳</span>
            <span className="text-sm font-medium">
              메시지 전송 제한에 도달했습니다.
            </span>
          </div>
          <div className="text-xs text-yellow-600 mt-1" data-testid="rate-limit-countdown">
            {Math.ceil(rateLimitStatus.timeUntilNextMessage / 1000)}초 후에 다시 시도해주세요.
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            disabled={isInputDisabled}
            maxLength={maxLength}
            rows={1}
            data-testid="chat-input"
            className={cn(
              'w-full resize-none rounded-lg border border-gray-300 px-4 py-3 pr-12',
              'focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20',
              'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
              'placeholder:text-gray-400',
              isFocused && 'border-blue-500 ring-2 ring-blue-500/20'
            )}
            style={{ minHeight: '48px' }}
          />
          
          {/* Character count */}
          <div className={cn(
            'absolute bottom-2 right-12 text-xs',
            remainingChars < 50 ? 'text-red-500' : 'text-gray-400'
          )}>
            {remainingChars}
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-xs text-gray-500">
            {rateLimitStatus && (
              <span>
                남은 메시지: {rateLimitStatus.remainingMessages}개
              </span>
            )}
            <span className="text-gray-400">
              Shift + Enter로 줄바꿈
            </span>
          </div>
          
          <Button
            type="submit"
            disabled={isInputDisabled || !message.trim()}
            data-testid="send-button"
            className={cn(
              'px-6 py-2 min-w-[80px]',
              isProcessing && 'cursor-not-allowed'
            )}
          >
            {isProcessing ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>전송중</span>
              </div>
            ) : (
              '전송'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}