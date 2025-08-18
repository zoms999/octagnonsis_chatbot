'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { ChatError, ChatErrorHandler, ErrorContext } from '@/lib/chat-error-handler';

interface ChatErrorState {
  currentError: ChatError | null;
  errorHistory: ChatError[];
  isShowingError: boolean;
  errorCount: number;
}

interface ChatErrorActions {
  handleError: (error: any, context?: ErrorContext) => ChatError;
  clearError: () => void;
  clearAllErrors: () => void;
  retryLastAction: () => void;
  dismissError: () => void;
}

interface UseChatErrorHandlerOptions {
  autoShow?: boolean;
  maxErrors?: number;
  errorTimeout?: number;
  onError?: (error: ChatError) => void;
  onRetry?: () => void;
}

/**
 * Hook for managing chat errors with user feedback and recovery actions
 * Implements requirements 2.3 and 4.4 for error handling and user feedback
 */
export function useChatErrorHandler(
  options: UseChatErrorHandlerOptions = {}
): ChatErrorState & ChatErrorActions {
  const {
    autoShow = true,
    maxErrors = 10,
    errorTimeout = 0, // 0 means no auto-hide
    onError,
    onRetry
  } = options;

  const [state, setState] = useState<ChatErrorState>({
    currentError: null,
    errorHistory: [],
    isShowingError: false,
    errorCount: 0
  });

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastActionRef = useRef<(() => void) | null>(null);

  // Handle new errors
  const handleError = useCallback((error: any, context: ErrorContext = {}): ChatError => {
    const chatError = ChatErrorHandler.processError(error, context);
    
    setState(prev => {
      const newHistory = [chatError, ...prev.errorHistory].slice(0, maxErrors);
      
      return {
        currentError: chatError,
        errorHistory: newHistory,
        isShowingError: autoShow,
        errorCount: prev.errorCount + 1
      };
    });

    // Call error callback
    if (onError) {
      onError(chatError);
    }

    // Set auto-hide timeout if specified
    if (errorTimeout > 0 && autoShow) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      timeoutRef.current = setTimeout(() => {
        setState(prev => ({
          ...prev,
          isShowingError: false
        }));
      }, errorTimeout);
    }

    // Log error for debugging
    console.error('Chat error handled:', {
      type: chatError.type,
      message: chatError.message,
      recoverable: chatError.recoverable,
      context
    });

    return chatError;
  }, [autoShow, maxErrors, errorTimeout, onError]);

  // Clear current error
  const clearError = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentError: null,
      isShowingError: false
    }));

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // Clear all errors
  const clearAllErrors = useCallback(() => {
    setState({
      currentError: null,
      errorHistory: [],
      isShowingError: false,
      errorCount: 0
    });

    ChatErrorHandler.clearErrorHistory();

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // Retry last action
  const retryLastAction = useCallback(() => {
    if (lastActionRef.current) {
      try {
        lastActionRef.current();
        clearError();
      } catch (error) {
        console.error('Failed to retry last action:', error);
        handleError(error, { endpoint: 'retry_action' });
      }
    } else if (onRetry) {
      onRetry();
      clearError();
    }
  }, [clearError, handleError, onRetry]);

  // Dismiss error (same as clear but with different semantic meaning)
  const dismissError = useCallback(() => {
    clearError();
  }, [clearError]);

  // Store retry action for later use
  const setRetryAction = useCallback((action: () => void) => {
    lastActionRef.current = action;
  }, []);

  // Listen for retry events from error components
  useEffect(() => {
    const handleRetryEvent = (event: CustomEvent) => {
      retryLastAction();
    };

    window.addEventListener('chat:retry-request', handleRetryEvent as EventListener);
    
    return () => {
      window.removeEventListener('chat:retry-request', handleRetryEvent as EventListener);
    };
  }, [retryLastAction]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    // State
    currentError: state.currentError,
    errorHistory: state.errorHistory,
    isShowingError: state.isShowingError,
    errorCount: state.errorCount,
    
    // Actions
    handleError,
    clearError,
    clearAllErrors,
    retryLastAction,
    dismissError,
    
    // Additional utility (not in interface but useful)
    setRetryAction
  } as ChatErrorState & ChatErrorActions & { setRetryAction: (action: () => void) => void };
}

/**
 * Hook for handling authentication-specific errors
 */
export function useAuthErrorHandler() {
  const errorHandler = useChatErrorHandler({
    autoShow: true,
    errorTimeout: 0, // Don't auto-hide auth errors
    onError: (error) => {
      if (error.type === 'auth') {
        // Dispatch auth error event for auth provider to handle
        window.dispatchEvent(new CustomEvent('auth:error', {
          detail: { error }
        }));
      }
    }
  });

  const handleAuthError = useCallback((error: any, context: ErrorContext = {}) => {
    return errorHandler.handleError(error, {
      ...context,
      endpoint: context.endpoint || 'auth'
    });
  }, [errorHandler]);

  return {
    ...errorHandler,
    handleAuthError
  };
}

/**
 * Hook for handling network-specific errors with retry logic
 */
export function useNetworkErrorHandler(maxRetries: number = 3) {
  const [retryCount, setRetryCount] = useState(0);
  
  const errorHandler = useChatErrorHandler({
    autoShow: true,
    errorTimeout: 5000, // Auto-hide network errors after 5 seconds
    onRetry: () => {
      setRetryCount(prev => prev + 1);
    }
  });

  const handleNetworkError = useCallback((error: any, context: ErrorContext = {}) => {
    const chatError = errorHandler.handleError(error, {
      ...context,
      endpoint: context.endpoint || 'network'
    });

    // Auto-retry for network errors if under retry limit
    if (chatError.type === 'network' && retryCount < maxRetries) {
      console.log(`Auto-retrying network request (${retryCount + 1}/${maxRetries})`);
      
      setTimeout(() => {
        errorHandler.retryLastAction();
      }, 1000 * Math.pow(2, retryCount)); // Exponential backoff
    }

    return chatError;
  }, [errorHandler, retryCount, maxRetries]);

  const resetRetryCount = useCallback(() => {
    setRetryCount(0);
  }, []);

  return {
    ...errorHandler,
    handleNetworkError,
    retryCount,
    resetRetryCount,
    canRetry: retryCount < maxRetries
  };
}

/**
 * Hook for handling validation errors with field-specific feedback
 */
export function useValidationErrorHandler() {
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const errorHandler = useChatErrorHandler({
    autoShow: true,
    errorTimeout: 0, // Don't auto-hide validation errors
    onError: (error) => {
      if (error.type === 'validation' && error.details?.fieldErrors) {
        setFieldErrors(error.details.fieldErrors);
      }
    }
  });

  const handleValidationError = useCallback((error: any, context: ErrorContext = {}) => {
    return errorHandler.handleError(error, {
      ...context,
      endpoint: context.endpoint || 'validation'
    });
  }, [errorHandler]);

  const clearFieldError = useCallback((fieldName: string) => {
    setFieldErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[fieldName];
      return newErrors;
    });
  }, []);

  const clearAllFieldErrors = useCallback(() => {
    setFieldErrors({});
  }, []);

  return {
    ...errorHandler,
    handleValidationError,
    fieldErrors,
    clearFieldError,
    clearAllFieldErrors,
    hasFieldErrors: Object.keys(fieldErrors).length > 0
  };
}