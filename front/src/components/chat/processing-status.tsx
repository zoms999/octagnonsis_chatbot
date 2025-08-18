'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface ProcessingStatusProps {
  status: 'processing' | 'generating' | 'complete' | 'error';
  progress?: number;
  currentStep?: string;
  className?: string;
}

export function ProcessingStatus({ 
  status, 
  progress, 
  currentStep,
  className 
}: ProcessingStatusProps) {
  const getStatusConfig = () => {
    switch (status) {
      case 'processing':
        return {
          color: 'bg-blue-500',
          text: '질문 분석 중...',
          icon: '🔍'
        };
      case 'generating':
        return {
          color: 'bg-green-500',
          text: '답변 생성 중...',
          icon: '✨'
        };
      case 'complete':
        return {
          color: 'bg-green-600',
          text: '완료',
          icon: '✅'
        };
      case 'error':
        return {
          color: 'bg-red-500',
          text: '오류 발생',
          icon: '❌'
        };
      default:
        return {
          color: 'bg-gray-500',
          text: '대기 중...',
          icon: '⏳'
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className={cn(
      'flex items-center gap-3 p-3 bg-gray-50 rounded-lg border',
      className
    )}>
      <div className="flex items-center gap-2">
        <span className="text-lg">{config.icon}</span>
        <span className="text-sm font-medium text-gray-700">
          {currentStep || config.text}
        </span>
      </div>
      
      {progress !== undefined && (
        <div className="flex-1 max-w-xs">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={cn(
                'h-2 rounded-full transition-all duration-300',
                config.color
              )}
              style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
            />
          </div>
          <div className="text-xs text-gray-500 mt-1 text-right">
            {Math.round(progress)}%
          </div>
        </div>
      )}
    </div>
  );
}