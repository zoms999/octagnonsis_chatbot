'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface TypingIndicatorProps {
  className?: string;
  status?: 'processing' | 'generating' | 'complete';
}

export function TypingIndicator({ className, status = 'processing' }: TypingIndicatorProps) {
  const getStatusText = () => {
    switch (status) {
      case 'processing':
        return '질문을 분석하고 있습니다...';
      case 'generating':
        return '답변을 생성하고 있습니다...';
      default:
        return '처리 중...';
    }
  };

  return (
    <div className={cn('flex justify-start w-full mb-4', className)}>
      <div className="bg-gray-100 rounded-lg px-4 py-3 mr-12 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.1s]" />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.2s]" />
          </div>
          <span className="text-sm text-gray-600">{getStatusText()}</span>
        </div>
      </div>
    </div>
  );
}