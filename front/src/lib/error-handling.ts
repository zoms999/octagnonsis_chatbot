import { 
  ApiError, 
  NetworkError, 
  AuthError, 
  RateLimitError, 
  ValidationError, 
  ServerError 
} from './types';
import { ApiErrorHandler } from './api';

// Error classification and handling utilities
export class ErrorHandler {
  // Handle different types of errors with appropriate user messages
  static getErrorMessage(error: unknown): string {
    if (!error) return 'An unknown error occurred';
    
    // Handle API errors
    if (typeof error === 'object' && 'message' in error) {
      const apiError = error as ApiError;
      
      switch (apiError.status) {
        case 400:
          return apiError.message || 'Invalid request. Please check your input.';
        case 401:
          return 'Authentication failed. Please log in again.';
        case 403:
          return 'You do not have permission to perform this action.';
        case 404:
          return 'The requested resource was not found.';
        case 429:
          return 'Too many requests. Please wait before trying again.';
        case 500:
          return 'Server error. Please try again later.';
        case 502:
        case 503:
        case 504:
          return 'Service temporarily unavailable. Please try again later.';
        default:
          return apiError.message || 'An error occurred. Please try again.';
      }
    }
    
    // Handle network errors
    if (error instanceof Error) {
      if (error.message.includes('fetch')) {
        return 'Network connection failed. Please check your internet connection.';
      }
      return error.message;
    }
    
    return 'An unexpected error occurred';
  }

  // Get user-friendly error title
  static getErrorTitle(error: unknown): string {
    if (!error) return 'Error';
    
    if (typeof error === 'object' && 'status' in error) {
      const apiError = error as ApiError;
      
      switch (apiError.status) {
        case 400:
          return 'Invalid Request';
        case 401:
          return 'Authentication Required';
        case 403:
          return 'Access Denied';
        case 404:
          return 'Not Found';
        case 429:
          return 'Rate Limited';
        case 500:
          return 'Server Error';
        case 502:
        case 503:
        case 504:
          return 'Service Unavailable';
        default:
          return 'Error';
      }
    }
    
    if (error instanceof Error && error.message.includes('fetch')) {
      return 'Connection Error';
    }
    
    return 'Error';
  }

  // Determine if error is retryable
  static isRetryable(error: unknown): boolean {
    if (!error || typeof error !== 'object') return false;
    
    const apiError = error as ApiError;
    
    // Don't retry auth or validation errors
    if (ApiErrorHandler.isAuthError(apiError) || ApiErrorHandler.isValidationError(apiError)) {
      return false;
    }
    
    // Retry network errors and server errors
    return ApiErrorHandler.isNetworkError(apiError) || 
           ApiErrorHandler.isServerError(apiError) ||
           apiError.status === 429; // Rate limit errors can be retried
  }

  // Get retry delay for rate limit errors
  static getRetryDelay(error: unknown): number {
    if (ApiErrorHandler.isRateLimitError(error)) {
      const rateLimitError = error as RateLimitError;
      return (rateLimitError.retry_after || 60) * 1000; // Convert to milliseconds
    }
    
    return 0;
  }

  // Handle authentication errors
  static handleAuthError(error: AuthError): void {
    // Clear tokens and redirect to login
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      
      // Dispatch custom event for auth context
      window.dispatchEvent(new CustomEvent('auth:logout', {
        detail: { reason: 'auth_error', error }
      }));
      
      // Redirect to login if not already there
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
  }

  // Handle rate limit errors
  static handleRateLimitError(error: RateLimitError): void {
    const retryAfter = error.retry_after || 60;
    
    // Dispatch custom event for UI components to handle
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('rate_limit', {
        detail: { retryAfter, error }
      }));
    }
  }

  // Log errors for debugging/monitoring
  static logError(error: unknown, context?: string): void {
    const errorInfo = {
      error: error instanceof Error ? {
        name: error.name,
        message: error.message,
        stack: error.stack,
      } : error,
      context,
      timestamp: new Date().toISOString(),
      userAgent: typeof window !== 'undefined' ? window.navigator.userAgent : 'server',
      url: typeof window !== 'undefined' ? window.location.href : 'server',
    };
    
    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Error logged:', errorInfo);
    }
    
    // In production, you would send this to your error tracking service
    // e.g., Sentry, LogRocket, etc.
  }
}

// Toast notification types for error display
export interface ToastNotification {
  id: string;
  type: 'error' | 'warning' | 'info' | 'success';
  title: string;
  message: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// Error notification factory
export class ErrorNotificationFactory {
  static createErrorNotification(error: unknown, context?: string): ToastNotification {
    const id = `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const title = ErrorHandler.getErrorTitle(error);
    const message = ErrorHandler.getErrorMessage(error);
    
    let duration = 5000; // Default 5 seconds
    let action: ToastNotification['action'];
    
    // Customize based on error type
    if (ApiErrorHandler.isRateLimitError(error)) {
      const retryDelay = ErrorHandler.getRetryDelay(error);
      duration = retryDelay;
      action = {
        label: 'Retry',
        onClick: () => {
          // Retry logic would be handled by the component
        }
      };
    } else if (ApiErrorHandler.isNetworkError(error)) {
      action = {
        label: 'Retry',
        onClick: () => {
          // Retry logic would be handled by the component
        }
      };
    }
    
    return {
      id,
      type: 'error',
      title,
      message,
      duration,
      action,
    };
  }

  static createWarningNotification(message: string, title = 'Warning'): ToastNotification {
    return {
      id: `warning-${Date.now()}`,
      type: 'warning',
      title,
      message,
      duration: 4000,
    };
  }

  static createInfoNotification(message: string, title = 'Info'): ToastNotification {
    return {
      id: `info-${Date.now()}`,
      type: 'info',
      title,
      message,
      duration: 3000,
    };
  }

  static createSuccessNotification(message: string, title = 'Success'): ToastNotification {
    return {
      id: `success-${Date.now()}`,
      type: 'success',
      title,
      message,
      duration: 3000,
    };
  }
}

// React Error Boundary utility
export interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: any;
}

export class ErrorBoundaryUtils {
  static getErrorBoundaryFallback(error: Error, errorInfo: any) {
    return {
      title: 'Something went wrong',
      message: process.env.NODE_ENV === 'development' 
        ? error.message 
        : 'An unexpected error occurred. Please refresh the page.',
      details: process.env.NODE_ENV === 'development' 
        ? {
            error: error.toString(),
            componentStack: errorInfo.componentStack,
          }
        : undefined,
    };
  }

  static shouldResetErrorBoundary(prevError: Error, nextError: Error): boolean {
    // Reset if it's a different error
    return prevError.message !== nextError.message;
  }
}

// Validation error helpers
export class ValidationErrorHelper {
  static getFieldErrors(error: ValidationError): Record<string, string> {
    const fieldErrors: Record<string, string> = {};
    
    if (error.field_errors) {
      Object.entries(error.field_errors).forEach(([field, messages]) => {
        fieldErrors[field] = Array.isArray(messages) ? messages[0] : messages;
      });
    }
    
    return fieldErrors;
  }

  static hasFieldError(error: ValidationError, fieldName: string): boolean {
    return !!(error.field_errors && error.field_errors[fieldName]);
  }

  static getFieldError(error: ValidationError, fieldName: string): string | undefined {
    if (!error.field_errors || !error.field_errors[fieldName]) {
      return undefined;
    }
    
    const messages = error.field_errors[fieldName];
    return Array.isArray(messages) ? messages[0] : messages;
  }
}

// Export all utilities
export { ErrorHandler as default };
export * from './types';