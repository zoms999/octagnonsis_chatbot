'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ApiErrorHandler } from '@/lib/api';
import { NetworkError } from '@/lib/types';

interface NetworkErrorHandlerProps {
  error: NetworkError;
  onRetry?: () => void;
  onDismiss?: () => void;
  autoRetry?: boolean;
  maxRetries?: number;
  retryDelay?: number;
  className?: string;
}

export const NetworkErrorHandler: React.FC<NetworkErrorHandlerProps> = ({
  error,
  onRetry,
  onDismiss,
  autoRetry = false,
  maxRetries = 3,
  retryDelay = 2000,
  className = '',
}) => {
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const [nextRetryIn, setNextRetryIn] = useState(0);

  // Auto-retry logic
  useEffect(() => {
    if (!autoRetry || !onRetry || retryCount >= maxRetries) return;

    const timer = setTimeout(() => {
      handleRetry();
    }, retryDelay * Math.pow(2, retryCount)); // Exponential backoff

    return () => clearTimeout(timer);
  }, [autoRetry, onRetry, retryCount, maxRetries, retryDelay]);

  // Countdown for next retry
  useEffect(() => {
    if (!autoRetry || retryCount >= maxRetries || !isRetrying) return;

    const delay = retryDelay * Math.pow(2, retryCount);
    setNextRetryIn(Math.ceil(delay / 1000));

    const countdown = setInterval(() => {
      setNextRetryIn((prev) => {
        if (prev <= 1) {
          clearInterval(countdown);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(countdown);
  }, [autoRetry, retryCount, maxRetries, isRetrying, retryDelay]);

  const handleRetry = useCallback(async () => {
    if (isRetrying) return;

    setIsRetrying(true);
    setRetryCount((prev) => prev + 1);

    try {
      await onRetry?.();
    } catch (error) {
      // Retry failed, will be handled by the effect above
    } finally {
      setIsRetrying(false);
    }
  }, [isRetrying, onRetry]);

  const getErrorMessage = (error: NetworkError): string => {
    if (error.message) return error.message;
    
    // Provide user-friendly messages based on error type
    if (error.code === 'NETWORK_ERROR') {
      return 'Unable to connect to the server. Please check your internet connection.';
    }
    
    if (error.code === 'TIMEOUT_ERROR') {
      return 'The request timed out. The server may be experiencing high load.';
    }
    
    if (error.code === 'CORS_ERROR') {
      return 'Cross-origin request blocked. Please contact support.';
    }
    
    return 'A network error occurred. Please try again.';
  };

  const getErrorIcon = () => {
    if (error.code === 'TIMEOUT_ERROR') {
      return (
        <svg className="h-5 w-5 text-orange-400" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
        </svg>
      );
    }
    
    return (
      <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
    );
  };

  const canRetry = retryCount < maxRetries;
  const isAutoRetrying = autoRetry && canRetry && !isRetrying;

  return (
    <Card className={`p-4 border-red-200 bg-red-50 ${className}`}>
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          {getErrorIcon()}
        </div>
        
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-red-800">
            {error.code === 'TIMEOUT_ERROR' ? 'Request Timeout' : 'Connection Error'}
          </h3>
          
          <div className="mt-1 text-sm text-red-700">
            <p>{getErrorMessage(error)}</p>
            
            {retryCount > 0 && (
              <p className="mt-1">
                Retry attempt {retryCount} of {maxRetries}
              </p>
            )}
            
            {isAutoRetrying && nextRetryIn > 0 && (
              <p className="mt-1 font-medium">
                Retrying automatically in {nextRetryIn} seconds...
              </p>
            )}
            
            {retryCount >= maxRetries && (
              <p className="mt-1 font-medium text-red-800">
                Maximum retry attempts reached. Please check your connection and try again.
              </p>
            )}
          </div>
          
          {isRetrying && (
            <div className="mt-3">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
                <span className="text-sm text-red-700">Retrying...</span>
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
            className="text-red-800 border-red-300 hover:bg-red-100"
          >
            Dismiss
          </Button>
        )}
        
        {onRetry && (
          <Button
            size="sm"
            onClick={handleRetry}
            disabled={isRetrying || (autoRetry && canRetry)}
            className="bg-red-600 hover:bg-red-700 text-white disabled:bg-gray-300 disabled:text-gray-500"
          >
            {isRetrying ? 'Retrying...' : canRetry ? 'Retry' : 'Max Retries Reached'}
          </Button>
        )}
      </div>
    </Card>
  );
};

// Hook for handling network errors with retry logic
export const useNetworkErrorHandler = (options: {
  maxRetries?: number;
  retryDelay?: number;
  autoRetry?: boolean;
} = {}) => {
  const { maxRetries = 3, retryDelay = 2000, autoRetry = false } = options;
  
  const [networkState, setNetworkState] = useState<{
    isOffline: boolean;
    hasNetworkError: boolean;
    error?: NetworkError;
    retryCount: number;
  }>({
    isOffline: false,
    hasNetworkError: false,
    retryCount: 0,
  });

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => {
      setNetworkState(prev => ({ ...prev, isOffline: false }));
    };

    const handleOffline = () => {
      setNetworkState(prev => ({ ...prev, isOffline: true }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Set initial state
    setNetworkState(prev => ({ ...prev, isOffline: !navigator.onLine }));

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const handleNetworkError = useCallback((error: unknown) => {
    if (ApiErrorHandler.isNetworkError(error)) {
      const networkError = error as NetworkError;
      setNetworkState(prev => ({
        ...prev,
        hasNetworkError: true,
        error: networkError,
        retryCount: 0,
      }));
    }
  }, []);

  const retryOperation = useCallback(async (
    operation: () => Promise<any>
  ): Promise<any> => {
    let lastError: unknown;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        setNetworkState(prev => ({ ...prev, retryCount: attempt }));
        const result = await operation();
        
        // Success - clear error state
        setNetworkState(prev => ({
          ...prev,
          hasNetworkError: false,
          error: undefined,
          retryCount: 0,
        }));
        
        return result;
      } catch (error) {
        lastError = error;
        
        // Don't retry if not a network error
        if (!ApiErrorHandler.isNetworkError(error)) {
          throw error;
        }
        
        // Don't retry on the last attempt
        if (attempt === maxRetries) {
          setNetworkState(prev => ({
            ...prev,
            hasNetworkError: true,
            error: error as NetworkError,
            retryCount: attempt + 1,
          }));
          throw error;
        }
        
        // Wait before retrying (exponential backoff)
        if (attempt < maxRetries) {
          await new Promise(resolve => 
            setTimeout(resolve, retryDelay * Math.pow(2, attempt))
          );
        }
      }
    }
    
    throw lastError;
  }, [maxRetries, retryDelay]);

  const clearNetworkError = useCallback(() => {
    setNetworkState(prev => ({
      ...prev,
      hasNetworkError: false,
      error: undefined,
      retryCount: 0,
    }));
  }, []);

  const isConnected = useCallback(() => {
    return !networkState.isOffline && navigator.onLine;
  }, [networkState.isOffline]);

  return {
    ...networkState,
    handleNetworkError,
    retryOperation,
    clearNetworkError,
    isConnected,
  };
};

export default NetworkErrorHandler;