'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { ApiErrorHandler } from '@/lib/api';
import { RateLimitError, NetworkError, ApiError } from '@/lib/types';
import RateLimitHandler from './rate-limit-handler';
import NetworkErrorHandler from './network-error-handler';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface ErrorRecoveryProps {
  error: unknown;
  onRetry?: () => void;
  onDismiss?: () => void;
  autoRetry?: boolean;
  maxRetries?: number;
  className?: string;
}

export const ErrorRecovery: React.FC<ErrorRecoveryProps> = ({
  error,
  onRetry,
  onDismiss,
  autoRetry = false,
  maxRetries = 3,
  className = '',
}) => {
  // Handle rate limit errors
  if (ApiErrorHandler.isRateLimitError(error)) {
    return (
      <RateLimitHandler
        error={error as RateLimitError}
        onRetry={onRetry}
        onDismiss={onDismiss}
        className={className}
      />
    );
  }

  // Handle network errors
  if (ApiErrorHandler.isNetworkError(error)) {
    return (
      <NetworkErrorHandler
        error={error as NetworkError}
        onRetry={onRetry}
        onDismiss={onDismiss}
        autoRetry={autoRetry}
        maxRetries={maxRetries}
        className={className}
      />
    );
  }

  // Handle other API errors
  if (ApiErrorHandler.isApiError(error)) {
    const apiError = error as ApiError;
    
    return (
      <Card className={`p-4 border-red-200 bg-red-50 ${className}`}>
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-red-800">
              {apiError.status === 500 ? 'Server Error' : 
               apiError.status === 404 ? 'Not Found' :
               apiError.status === 403 ? 'Access Denied' :
               'Error'}
            </h3>
            
            <div className="mt-1 text-sm text-red-700">
              <p>{apiError.message || 'An error occurred. Please try again.'}</p>
            </div>
          </div>
        </div>
        
        <div className="mt-4 flex justify-end space-x-2">
          {onDismiss && (
            <Button
              variant="outline"
              size="sm"
              onClick={onDismiss}
              className="text-red-800 border-red-300 hover:bg-red-100"
            >
              Dismiss
            </Button>
          )}
          
          {onRetry && ApiErrorHandler.isRetryableError(error) && (
            <Button
              size="sm"
              onClick={onRetry}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Retry
            </Button>
          )}
        </div>
      </Card>
    );
  }

  // Handle unknown errors
  return (
    <Card className={`p-4 border-gray-200 bg-gray-50 ${className}`}>
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <svg className="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </div>
        
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-800">
            Unexpected Error
          </h3>
          
          <div className="mt-1 text-sm text-gray-700">
            <p>An unexpected error occurred. Please try again.</p>
          </div>
        </div>
      </div>
      
      <div className="mt-4 flex justify-end space-x-2">
        {onDismiss && (
          <Button
            variant="outline"
            size="sm"
            onClick={onDismiss}
            className="text-gray-800 border-gray-300 hover:bg-gray-100"
          >
            Dismiss
          </Button>
        )}
        
        {onRetry && (
          <Button
            size="sm"
            onClick={onRetry}
            className="bg-gray-600 hover:bg-gray-700 text-white"
          >
            Retry
          </Button>
        )}
      </div>
    </Card>
  );
};

// Hook for comprehensive error recovery
export const useErrorRecovery = (options: {
  maxRetries?: number;
  retryDelay?: number;
  autoRetry?: boolean;
  onError?: (error: unknown) => void;
} = {}) => {
  const {
    maxRetries = 3,
    retryDelay = 2000,
    autoRetry = false,
    onError,
  } = options;

  const [errorState, setErrorState] = useState<{
    error?: unknown;
    retryCount: number;
    isRetrying: boolean;
    canRetry: boolean;
  }>({
    retryCount: 0,
    isRetrying: false,
    canRetry: true,
  });

  const handleError = useCallback((error: unknown) => {
    setErrorState(prev => ({
      ...prev,
      error,
      retryCount: 0,
      canRetry: true,
    }));
    
    onError?.(error);
  }, [onError]);

  const retry = useCallback(async (operation: () => Promise<any>) => {
    if (!errorState.canRetry || errorState.isRetrying) return;

    setErrorState(prev => ({
      ...prev,
      isRetrying: true,
      retryCount: prev.retryCount + 1,
    }));

    try {
      const result = await operation();
      
      // Success - clear error state
      setErrorState({
        retryCount: 0,
        isRetrying: false,
        canRetry: true,
      });
      
      return result;
    } catch (error) {
      const newRetryCount = errorState.retryCount + 1;
      const canStillRetry = newRetryCount < maxRetries && 
                           (ApiErrorHandler.isNetworkError(error) || 
                            ApiErrorHandler.isServerError(error));
      
      setErrorState(prev => ({
        ...prev,
        error,
        isRetrying: false,
        canRetry: canStillRetry,
      }));
      
      // Auto-retry if enabled and possible
      if (autoRetry && canStillRetry) {
        setTimeout(() => {
          retry(operation);
        }, retryDelay * Math.pow(2, newRetryCount - 1));
      }
      
      throw error;
    }
  }, [errorState, maxRetries, retryDelay, autoRetry]);

  const clearError = useCallback(() => {
    setErrorState({
      retryCount: 0,
      isRetrying: false,
      canRetry: true,
    });
  }, []);

  const executeWithRecovery = useCallback(async (
    operation: () => Promise<any>
  ) => {
    try {
      return await operation();
    } catch (error) {
      handleError(error);
      throw error;
    }
  }, [handleError]);

  return {
    ...errorState,
    handleError,
    retry,
    clearError,
    executeWithRecovery,
  };
};

export default ErrorRecovery;