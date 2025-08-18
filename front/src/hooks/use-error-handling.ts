'use client';

import { useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { ApiErrorHandler } from '@/lib/api';
import { ErrorHandler } from '@/lib/error-handling';
import { useToast } from '@/providers/toast-provider';
import { useAuth } from '@/providers/auth-provider';
import { ApiError, RateLimitError } from '@/lib/types';

interface UseErrorHandlingOptions {
  showToast?: boolean;
  redirectOnAuth?: boolean;
  logErrors?: boolean;
}

export const useErrorHandling = (options: UseErrorHandlingOptions = {}) => {
  const {
    showToast = true,
    redirectOnAuth = true,
    logErrors = true,
  } = options;

  const { showError, showWarning } = useToast();
  const { logout } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  // Handle different types of errors
  const handleError = useCallback((error: unknown, context?: string) => {
    // Log error if enabled
    if (logErrors) {
      ErrorHandler.logError(error, context);
    }

    // Handle authentication errors
    if (ApiErrorHandler.isAuthError(error)) {
      if (redirectOnAuth) {
        logout();
        router.push('/login');
      }
      
      if (showToast) {
        showError(error, context);
      }
      return;
    }

    // Handle rate limit errors with special UI
    if (ApiErrorHandler.isRateLimitError(error)) {
      const rateLimitError = error as RateLimitError;
      const retryAfter = rateLimitError.retry_after || 60;
      
      if (showToast) {
        showWarning(
          `Too many requests. Please wait ${retryAfter} seconds before trying again.`,
          'Rate Limited'
        );
      }
      return;
    }

    // Handle validation errors (usually handled by forms, but show if requested)
    if (ApiErrorHandler.isValidationError(error)) {
      if (showToast) {
        showError(error, context);
      }
      return;
    }

    // Handle network errors
    if (ApiErrorHandler.isNetworkError(error)) {
      if (showToast) {
        showError(error, context);
      }
      return;
    }

    // Handle server errors
    if (ApiErrorHandler.isServerError(error)) {
      if (showToast) {
        showError(error, context);
      }
      return;
    }

    // Handle unknown errors
    if (showToast) {
      showError(error, context);
    }
  }, [showError, showWarning, logout, router, redirectOnAuth, showToast, logErrors]);

  // Handle React Query errors specifically
  const handleQueryError = useCallback((error: unknown, context?: string) => {
    handleError(error, context || 'Query Error');
  }, [handleError]);

  // Handle mutation errors specifically
  const handleMutationError = useCallback((error: unknown, context?: string) => {
    handleError(error, context || 'Mutation Error');
  }, [handleError]);

  // Retry function for failed operations
  const retryOperation = useCallback(async (
    operation: () => Promise<any>,
    maxRetries = 3,
    delay = 1000
  ) => {
    let lastError: unknown;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        
        // Don't retry on auth or validation errors
        if (ApiErrorHandler.isAuthError(error) || ApiErrorHandler.isValidationError(error)) {
          throw error;
        }
        
        // Don't retry on the last attempt
        if (attempt === maxRetries) {
          throw error;
        }
        
        // Wait before retrying (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt)));
      }
    }
    
    throw lastError;
  }, []);

  // Clear error state (useful for resetting error boundaries)
  const clearErrors = useCallback(() => {
    // Clear React Query errors
    queryClient.clear();
    
    // Dispatch clear errors event
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('errors:clear'));
    }
  }, [queryClient]);

  // Check if error is retryable
  const isRetryable = useCallback((error: unknown): boolean => {
    return ErrorHandler.isRetryable(error);
  }, []);

  // Get retry delay for rate limit errors
  const getRetryDelay = useCallback((error: unknown): number => {
    return ErrorHandler.getRetryDelay(error);
  }, []);

  return {
    handleError,
    handleQueryError,
    handleMutationError,
    retryOperation,
    clearErrors,
    isRetryable,
    getRetryDelay,
  };
};

// Hook for handling form errors specifically
export const useFormErrorHandling = () => {
  const { handleError } = useErrorHandling({ showToast: false });

  const handleFormError = useCallback((error: unknown): Record<string, string> => {
    // Log the error
    ErrorHandler.logError(error, 'Form Error');

    // Handle validation errors
    if (ApiErrorHandler.isValidationError(error)) {
      const validationError = error as any;
      const fieldErrors: Record<string, string> = {};
      
      if (validationError.field_errors) {
        Object.entries(validationError.field_errors).forEach(([field, messages]) => {
          fieldErrors[field] = Array.isArray(messages) ? messages[0] : messages;
        });
      }
      
      return fieldErrors;
    }

    // Handle other errors
    handleError(error, 'Form submission failed');
    return {};
  }, [handleError]);

  return { handleFormError };
};

// Hook for handling async operations with error handling
export const useAsyncOperation = () => {
  const { handleError, retryOperation } = useErrorHandling();

  const executeAsync = useCallback(async <T>(
    operation: () => Promise<T>,
    options: {
      onSuccess?: (result: T) => void;
      onError?: (error: unknown) => void;
      showSuccessToast?: boolean;
      successMessage?: string;
      retries?: number;
    } = {}
  ): Promise<T | null> => {
    const {
      onSuccess,
      onError,
      showSuccessToast = false,
      successMessage = 'Operation completed successfully',
      retries = 0,
    } = options;

    try {
      const result = retries > 0 
        ? await retryOperation(operation, retries)
        : await operation();
      
      if (onSuccess) {
        onSuccess(result);
      }
      
      if (showSuccessToast) {
        // Dispatch success event for toast
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('global:success', {
            detail: { message: successMessage }
          }));
        }
      }
      
      return result;
    } catch (error) {
      if (onError) {
        onError(error);
      } else {
        handleError(error, 'Async operation failed');
      }
      
      return null;
    }
  }, [handleError, retryOperation]);

  return { executeAsync };
};

export default useErrorHandling;