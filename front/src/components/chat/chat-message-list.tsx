'use client';

import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '@/lib/types';
import { ChatBubble } from './chat-bubble';
import { TypingIndicator } from './typing-indicator';
import { cn } from '@/lib/utils';

interface ChatMessageListProps {
  messages: ChatMessage[];
  isTyping?: boolean;
  typingStatus?: 'processing' | 'generating' | 'complete';
  className?: string;
}

export function ChatMessageList({ 
  messages, 
  isTyping = false, 
  typingStatus = 'processing',
  className 
}: ChatMessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    const scrollToBottom = () => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ 
          behavior: 'smooth',
          block: 'end'
        });
      }
    };

    // Small delay to ensure DOM is updated
    const timeoutId = setTimeout(scrollToBottom, 100);
    return () => clearTimeout(timeoutId);
  }, [messages, isTyping]);

  // Handle scroll behavior for better UX
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let isUserScrolling = false;
    let scrollTimeout: NodeJS.Timeout;

    const handleScroll = () => {
      isUserScrolling = true;
      clearTimeout(scrollTimeout);
      
      // Reset user scrolling flag after 1 second of no scrolling
      scrollTimeout = setTimeout(() => {
        isUserScrolling = false;
      }, 1000);
    };

    container.addEventListener('scroll', handleScroll);
    return () => {
      container.removeEventListener('scroll', handleScroll);
      clearTimeout(scrollTimeout);
    };
  }, []);

  if (messages.length === 0 && !isTyping) {
    return (
      <div className={cn(
        'flex-1 flex items-center justify-center p-8',
        className
      )}>
        <div className="text-center text-gray-500">
          <div className="text-lg mb-2">💬</div>
          <p className="text-sm">
            안녕하세요! 적성 분석에 대해 궁금한 것이 있으시면 언제든 물어보세요.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={cn(
        'flex-1 overflow-y-auto p-4 space-y-0',
        className
      )}
      data-testid="chat-messages"
    >
      {messages.map((message) => (
        <ChatBubble 
          key={message.id} 
          message={message}
        />
      ))}
      
      {isTyping && (
        <TypingIndicator status={typingStatus} />
      )}
      
      {/* Invisible element to scroll to */}
      <div ref={messagesEndRef} />
    </div>
  );
}