'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ApiErrorHandler } from '@/lib/api';
import { RateLimitError } from '@/lib/types';

interface RateLimitHandlerProps {
  error: RateLimitError;
  onRetry?: () => void;
  onDismiss?: () => void;
  showCountdown?: boolean;
  className?: string;
}

export const RateLimitHandler: React.FC<RateLimitHandlerProps> = ({
  error,
  onRetry,
  onDismiss,
  showCountdown = true,
  className = '',
}) => {
  const [timeRemaining, setTimeRemaining] = useState(error.retry_after || 60);
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    if (!showCountdown || !isActive) return;

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          setIsActive(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [showCountdown, isActive]);

  const handleRetry = useCallback(() => {
    if (timeRemaining > 0) return;
    onRetry?.();
  }, [timeRemaining, onRetry]);

  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <Card className={`p-4 border-yellow-200 bg-yellow-50 ${className}`}>
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-yellow-400"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-yellow-800">
            Rate Limit Exceeded
          </h3>
          
          <div className="mt-1 text-sm text-yellow-700">
            <p>{error.message || 'Too many requests. Please wait before trying again.'}</p>
            
            {showCountdown && timeRemaining > 0 && (
              <p className="mt-2 font-medium">
                Please wait {formatTime(timeRemaining)} before retrying.
              </p>
            )}
            
            {timeRemaining === 0 && (
              <p className="mt-2 font-medium text-green-700">
                You can now retry your request.
              </p>
            )}
          </div>
          
          {showCountdown && timeRemaining > 0 && (
            <div className="mt-3">
              <div className="w-full bg-yellow-200 rounded-full h-2">
                <div
                  className="bg-yellow-600 h-2 rounded-full transition-all duration-1000 ease-linear"
                  style={{
                    width: `${((error.retry_after || 60) - timeRemaining) / (error.retry_after || 60) * 100}%`,
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
      
      <div className="mt-4 flex justify-end space-x-2">
        {onDismiss && (
          <Button
            variant="outline"
            size="sm"
            onClick={onDismiss}
            className="text-yellow-800 border-yellow-300 hover:bg-yellow-100"
          >
            Dismiss
          </Button>
        )}
        
        {onRetry && (
          <Button
            size="sm"
            onClick={handleRetry}
            disabled={timeRemaining > 0}
            className={
              timeRemaining > 0
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-yellow-600 hover:bg-yellow-700 text-white'
            }
          >
            {timeRemaining > 0 ? `Retry in ${formatTime(timeRemaining)}` : 'Retry Now'}
          </Button>
        )}
      </div>
    </Card>
  );
};

// Hook for handling rate limit errors
export const useRateLimitHandler = () => {
  const [rateLimitState, setRateLimitState] = useState<{
    isRateLimited: boolean;
    error?: RateLimitError;
    retryAfter?: number;
  }>({
    isRateLimited: false,
  });

  const handleRateLimitError = useCallback((error: unknown) => {
    if (ApiErrorHandler.isRateLimitError(error)) {
      const rateLimitError = error as RateLimitError;
      setRateLimitState({
        isRateLimited: true,
        error: rateLimitError,
        retryAfter: rateLimitError.retry_after || 60,
      });
      
      // Auto-clear after retry period
      setTimeout(() => {
        setRateLimitState({ isRateLimited: false });
      }, (rateLimitError.retry_after || 60) * 1000);
    }
  }, []);

  const clearRateLimit = useCallback(() => {
    setRateLimitState({ isRateLimited: false });
  }, []);

  const canRetry = useCallback(() => {
    return !rateLimitState.isRateLimited;
  }, [rateLimitState.isRateLimited]);

  return {
    ...rateLimitState,
    handleRateLimitError,
    clearRateLimit,
    canRetry,
  };
};

export default RateLimitHandler;