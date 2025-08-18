/**
 * Enhanced error handling system for chat functionality
 * Implements requirements 2.3 and 4.4 for comprehensive error handling and user feedback
 */

export interface ChatError {
  type: 'network' | 'auth' | 'validation' | 'server' | 'timeout' | 'unknown';
  message: string;
  code?: string;
  status?: number;
  details?: any;
  timestamp: Date;
  recoverable: boolean;
  userMessage: string;
  actionRequired?: 'login' | 'retry' | 'refresh' | 'contact_support';
}

export interface ErrorContext {
  userId?: string;
  conversationId?: string;
  question?: string;
  endpoint?: string;
  requestPayload?: any;
  responseData?: any;
}

/**
 * Chat-specific error handler with user-friendly messages and recovery actions
 */
export class ChatErrorHandler {
  private static errorHistory: ChatError[] = [];
  private static maxHistorySize = 50;

  /**
   * Process and classify errors from chat operations
   */
  static processError(error: any, context: ErrorContext = {}): ChatError {
    const timestamp = new Date();
    let chatError: ChatError;

    // Network errors
    if (this.isNetworkError(error)) {
      chatError = {
        type: 'network',
        message: error.message || 'Network connection failed',
        code: 'NETWORK_ERROR',
        timestamp,
        recoverable: true,
        userMessage: '네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인하고 다시 시도해주세요.',
        actionRequired: 'retry',
        details: { context }
      };
    }
    // Authentication errors
    else if (this.isAuthError(error)) {
      chatError = {
        type: 'auth',
        message: error.message || 'Authentication failed',
        code: 'AUTH_ERROR',
        status: error.status || 401,
        timestamp,
        recoverable: true,
        userMessage: '로그인이 필요하거나 세션이 만료되었습니다. 다시 로그인해주세요.',
        actionRequired: 'login',
        details: { context }
      };
    }
    // Validation errors
    else if (this.isValidationError(error)) {
      chatError = {
        type: 'validation',
        message: error.message || 'Invalid request data',
        code: 'VALIDATION_ERROR',
        status: error.status || 400,
        timestamp,
        recoverable: true,
        userMessage: '입력한 내용에 문제가 있습니다. 다시 확인하고 시도해주세요.',
        actionRequired: 'retry',
        details: { 
          context,
          fieldErrors: error.field_errors 
        }
      };
    }
    // Server errors
    else if (this.isServerError(error)) {
      chatError = {
        type: 'server',
        message: error.message || 'Server error occurred',
        code: 'SERVER_ERROR',
        status: error.status || 500,
        timestamp,
        recoverable: true,
        userMessage: '서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.',
        actionRequired: 'retry',
        details: { context }
      };
    }
    // Timeout errors
    else if (this.isTimeoutError(error)) {
      chatError = {
        type: 'timeout',
        message: error.message || 'Request timed out',
        code: 'TIMEOUT_ERROR',
        timestamp,
        recoverable: true,
        userMessage: '요청 시간이 초과되었습니다. 네트워크 상태를 확인하고 다시 시도해주세요.',
        actionRequired: 'retry',
        details: { context }
      };
    }
    // Unknown errors
    else {
      chatError = {
        type: 'unknown',
        message: error.message || 'An unexpected error occurred',
        code: 'UNKNOWN_ERROR',
        timestamp,
        recoverable: false,
        userMessage: '예상치 못한 오류가 발생했습니다. 페이지를 새로고침하거나 지원팀에 문의해주세요.',
        actionRequired: 'refresh',
        details: { 
          context,
          originalError: error.toString()
        }
      };
    }

    // Add to error history
    this.addToHistory(chatError);

    // Log error for debugging
    this.logError(chatError, context);

    return chatError;
  }

  /**
   * Get user-friendly error message with recovery instructions
   */
  static getUserMessage(error: ChatError): string {
    let message = error.userMessage;

    // Add specific recovery instructions based on action required
    switch (error.actionRequired) {
      case 'login':
        message += '\n\n로그인 페이지로 이동하시겠습니까?';
        break;
      case 'retry':
        message += '\n\n다시 시도 버튼을 클릭해주세요.';
        break;
      case 'refresh':
        message += '\n\n페이지를 새로고침해주세요.';
        break;
      case 'contact_support':
        message += '\n\n문제가 지속되면 지원팀에 문의해주세요.';
        break;
    }

    return message;
  }

  /**
   * Check if error is recoverable and suggest recovery action
   */
  static getRecoveryAction(error: ChatError): {
    canRecover: boolean;
    action: string;
    buttonText: string;
    handler: () => void;
  } {
    switch (error.actionRequired) {
      case 'login':
        return {
          canRecover: true,
          action: 'redirect_login',
          buttonText: '로그인하기',
          handler: () => {
            const currentPath = window.location.pathname;
            const loginUrl = `/login?returnTo=${encodeURIComponent(currentPath)}`;
            window.location.href = loginUrl;
          }
        };
      case 'retry':
        return {
          canRecover: true,
          action: 'retry_request',
          buttonText: '다시 시도',
          handler: () => {
            // This will be handled by the component
            window.dispatchEvent(new CustomEvent('chat:retry-request', {
              detail: { error }
            }));
          }
        };
      case 'refresh':
        return {
          canRecover: true,
          action: 'refresh_page',
          buttonText: '페이지 새로고침',
          handler: () => {
            window.location.reload();
          }
        };
      default:
        return {
          canRecover: false,
          action: 'none',
          buttonText: '확인',
          handler: () => {}
        };
    }
  }

  /**
   * Error type detection methods
   */
  private static isNetworkError(error: any): boolean {
    return error?.type === 'network_error' ||
           error?.code === 'NETWORK_ERROR' ||
           (error instanceof TypeError && error.message.includes('fetch')) ||
           error?.message?.includes('Network') ||
           error?.message?.includes('Failed to fetch');
  }

  private static isAuthError(error: any): boolean {
    return error?.type === 'auth_error' ||
           error?.status === 401 ||
           error?.status === 403 ||
           error?.code === 'AUTH_ERROR' ||
           error?.message?.includes('Unauthorized') ||
           error?.message?.includes('Authentication');
  }

  private static isValidationError(error: any): boolean {
    return error?.type === 'validation_error' ||
           error?.status === 400 ||
           error?.code === 'VALIDATION_ERROR' ||
           error?.field_errors;
  }

  private static isServerError(error: any): boolean {
    return error?.type === 'server_error' ||
           (error?.status >= 500 && error?.status < 600) ||
           error?.code === 'SERVER_ERROR';
  }

  private static isTimeoutError(error: any): boolean {
    return error?.code === 'TIMEOUT_ERROR' ||
           error?.name === 'AbortError' ||
           error?.message?.includes('timeout') ||
           error?.message?.includes('timed out');
  }

  /**
   * Add error to history for debugging and analytics
   */
  private static addToHistory(error: ChatError): void {
    this.errorHistory.unshift(error);
    
    // Keep history size manageable
    if (this.errorHistory.length > this.maxHistorySize) {
      this.errorHistory = this.errorHistory.slice(0, this.maxHistorySize);
    }
  }

  /**
   * Get error history for debugging
   */
  static getErrorHistory(): ChatError[] {
    return [...this.errorHistory];
  }

  /**
   * Clear error history
   */
  static clearErrorHistory(): void {
    this.errorHistory = [];
  }

  /**
   * Get error statistics
   */
  static getErrorStats(): {
    total: number;
    byType: Record<string, number>;
    recent: ChatError[];
    recoverable: number;
  } {
    const byType: Record<string, number> = {};
    let recoverable = 0;

    this.errorHistory.forEach(error => {
      byType[error.type] = (byType[error.type] || 0) + 1;
      if (error.recoverable) recoverable++;
    });

    return {
      total: this.errorHistory.length,
      byType,
      recent: this.errorHistory.slice(0, 5),
      recoverable
    };
  }

  /**
   * Log error for debugging and monitoring
   */
  private static logError(error: ChatError, context: ErrorContext): void {
    const logData = {
      error: {
        type: error.type,
        message: error.message,
        code: error.code,
        status: error.status,
        recoverable: error.recoverable,
        actionRequired: error.actionRequired
      },
      context,
      timestamp: error.timestamp.toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    // Console logging for development
    if (process.env.NODE_ENV === 'development') {
      console.group('🚨 Chat Error Occurred');
      console.error('Error Details:', logData);
      console.log('User Message:', error.userMessage);
      console.log('Recovery Action:', this.getRecoveryAction(error));
      console.groupEnd();
    }

    // Send to monitoring service in production
    if (process.env.NODE_ENV === 'production') {
      // This would integrate with your monitoring service
      // Example: Sentry, LogRocket, etc.
      try {
        // window.analytics?.track('Chat Error', logData);
      } catch (e) {
        console.warn('Failed to send error to monitoring service:', e);
      }
    }
  }

  /**
   * Create error from API response
   */
  static fromApiError(apiError: any, context: ErrorContext = {}): ChatError {
    return this.processError(apiError, context);
  }

  /**
   * Create error from exception
   */
  static fromException(exception: Error, context: ErrorContext = {}): ChatError {
    return this.processError(exception, context);
  }
}

/**
 * Utility functions for error handling in components
 */
export const ChatErrorUtils = {
  /**
   * Format error for display in UI
   */
  formatErrorForDisplay(error: ChatError): {
    title: string;
    message: string;
    severity: 'error' | 'warning' | 'info';
    showDetails: boolean;
  } {
    let severity: 'error' | 'warning' | 'info' = 'error';
    let showDetails = false;

    // Adjust severity based on error type
    switch (error.type) {
      case 'network':
      case 'timeout':
        severity = 'warning';
        break;
      case 'validation':
        severity = 'info';
        showDetails = true;
        break;
      case 'auth':
        severity = 'warning';
        break;
      default:
        severity = 'error';
        showDetails = process.env.NODE_ENV === 'development';
    }

    return {
      title: this.getErrorTitle(error.type),
      message: ChatErrorHandler.getUserMessage(error),
      severity,
      showDetails
    };
  },

  /**
   * Get appropriate title for error type
   */
  getErrorTitle(errorType: string): string {
    switch (errorType) {
      case 'network':
        return '연결 오류';
      case 'auth':
        return '인증 오류';
      case 'validation':
        return '입력 오류';
      case 'server':
        return '서버 오류';
      case 'timeout':
        return '시간 초과';
      default:
        return '오류 발생';
    }
  },

  /**
   * Check if error should be shown to user
   */
  shouldShowToUser(error: ChatError): boolean {
    // Always show recoverable errors
    if (error.recoverable) return true;
    
    // Show auth errors
    if (error.type === 'auth') return true;
    
    // Show validation errors
    if (error.type === 'validation') return true;
    
    // Don't show unknown errors in production unless critical
    if (error.type === 'unknown' && process.env.NODE_ENV === 'production') {
      return false;
    }
    
    return true;
  }
};