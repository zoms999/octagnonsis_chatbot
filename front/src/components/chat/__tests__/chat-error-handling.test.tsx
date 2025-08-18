import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ChatErrorDisplay, ChatErrorToast } from '../chat-error-display';
import { ChatErrorHandler } from '@/lib/chat-error-handler';
import { useChatErrorHandler } from '@/hooks/use-chat-error-handler';

// Mock components for testing
const TestErrorComponent = ({ error, onRetry }: { error: any; onRetry?: () => void }) => {
  const errorHandler = useChatErrorHandler({
    onRetry
  });

  React.useEffect(() => {
    if (error) {
      errorHandler.handleError(error);
    }
  }, [error, errorHandler]);

  return (
    <div>
      {errorHandler.isShowingError && errorHandler.currentError && (
        <ChatErrorDisplay
          error={errorHandler.currentError}
          onDismiss={errorHandler.dismissError}
          onRetry={errorHandler.retryLastAction}
          data-testid="error-display"
        />
      )}
    </div>
  );
};

describe('Chat Error Handling', () => {
  beforeEach(() => {
    // Clear error history before each test
    ChatErrorHandler.clearErrorHistory();
    
    // Mock console methods
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('ChatErrorHandler', () => {
    it('should classify network errors correctly', () => {
      const networkError = new Error('Failed to fetch');
      networkError.name = 'TypeError';
      
      const chatError = ChatErrorHandler.processError(networkError, {
        endpoint: '/api/chat/question'
      });

      expect(chatError.type).toBe('network');
      expect(chatError.recoverable).toBe(true);
      expect(chatError.actionRequired).toBe('retry');
      expect(chatError.userMessage).toContain('네트워크 연결');
    });

    it('should classify authentication errors correctly', () => {
      const authError = {
        status: 401,
        message: 'Unauthorized',
        type: 'auth_error'
      };
      
      const chatError = ChatErrorHandler.processError(authError, {
        userId: 'test-user',
        endpoint: '/api/chat/question'
      });

      expect(chatError.type).toBe('auth');
      expect(chatError.recoverable).toBe(true);
      expect(chatError.actionRequired).toBe('login');
      expect(chatError.userMessage).toContain('로그인이 필요');
    });

    it('should classify validation errors correctly', () => {
      const validationError = {
        status: 400,
        message: 'Invalid input',
        type: 'validation_error',
        field_errors: { question: 'Question is required' }
      };
      
      const chatError = ChatErrorHandler.processError(validationError, {
        question: '',
        endpoint: '/api/chat/question'
      });

      expect(chatError.type).toBe('validation');
      expect(chatError.recoverable).toBe(true);
      expect(chatError.actionRequired).toBe('retry');
      expect(chatError.userMessage).toContain('입력한 내용');
    });

    it('should classify server errors correctly', () => {
      const serverError = {
        status: 500,
        message: 'Internal Server Error',
        type: 'server_error'
      };
      
      const chatError = ChatErrorHandler.processError(serverError, {
        endpoint: '/api/chat/question'
      });

      expect(chatError.type).toBe('server');
      expect(chatError.recoverable).toBe(true);
      expect(chatError.actionRequired).toBe('retry');
      expect(chatError.userMessage).toContain('서버에 일시적인 문제');
    });

    it('should classify timeout errors correctly', () => {
      const timeoutError = new Error('Request timed out');
      timeoutError.name = 'AbortError';
      
      const chatError = ChatErrorHandler.processError(timeoutError, {
        endpoint: '/api/chat/question'
      });

      expect(chatError.type).toBe('timeout');
      expect(chatError.recoverable).toBe(true);
      expect(chatError.actionRequired).toBe('retry');
      expect(chatError.userMessage).toContain('요청 시간이 초과');
    });

    it('should provide correct recovery actions', () => {
      const authError = ChatErrorHandler.processError({
        status: 401,
        type: 'auth_error'
      });

      const recoveryAction = ChatErrorHandler.getRecoveryAction(authError);
      
      expect(recoveryAction.canRecover).toBe(true);
      expect(recoveryAction.action).toBe('redirect_login');
      expect(recoveryAction.buttonText).toBe('로그인하기');
    });

    it('should maintain error history', () => {
      const error1 = ChatErrorHandler.processError(new Error('Error 1'));
      const error2 = ChatErrorHandler.processError(new Error('Error 2'));
      
      const history = ChatErrorHandler.getErrorHistory();
      
      expect(history).toHaveLength(2);
      expect(history[0].message).toBe('Error 2'); // Most recent first
      expect(history[1].message).toBe('Error 1');
    });

    it('should provide error statistics', () => {
      ChatErrorHandler.processError({ status: 401, type: 'auth_error' });
      ChatErrorHandler.processError({ status: 500, type: 'server_error' });
      ChatErrorHandler.processError(new Error('Network error'));
      
      const stats = ChatErrorHandler.getErrorStats();
      
      expect(stats.total).toBe(3);
      expect(stats.byType.auth).toBe(1);
      expect(stats.byType.server).toBe(1);
      expect(stats.byType.unknown).toBe(1);
      expect(stats.recoverable).toBe(3); // All should be recoverable
    });
  });

  describe('ChatErrorDisplay Component', () => {
    it('should render network error correctly', () => {
      const networkError = ChatErrorHandler.processError(new Error('Failed to fetch'));
      
      render(
        <ChatErrorDisplay
          error={networkError}
          data-testid="error-display"
        />
      );

      expect(screen.getByText('연결 오류')).toBeInTheDocument();
      expect(screen.getByText(/네트워크 연결에 문제가 있습니다/)).toBeInTheDocument();
      expect(screen.getByText('다시 시도')).toBeInTheDocument();
    });

    it('should render authentication error correctly', () => {
      const authError = ChatErrorHandler.processError({
        status: 401,
        type: 'auth_error'
      });
      
      render(
        <ChatErrorDisplay
          error={authError}
          data-testid="error-display"
        />
      );

      expect(screen.getByText('인증 오류')).toBeInTheDocument();
      expect(screen.getByText(/로그인이 필요하거나 세션이 만료/)).toBeInTheDocument();
      expect(screen.getByText('로그인하기')).toBeInTheDocument();
    });

    it('should handle retry action', async () => {
      const retryMock = vi.fn();
      const networkError = ChatErrorHandler.processError(new Error('Failed to fetch'));
      
      render(
        <ChatErrorDisplay
          error={networkError}
          onRetry={retryMock}
          data-testid="error-display"
        />
      );

      const retryButton = screen.getByText('다시 시도');
      fireEvent.click(retryButton);

      expect(retryMock).toHaveBeenCalledTimes(1);
    });

    it('should handle dismiss action', async () => {
      const dismissMock = vi.fn();
      const networkError = ChatErrorHandler.processError(new Error('Failed to fetch'));
      
      render(
        <ChatErrorDisplay
          error={networkError}
          onDismiss={dismissMock}
          data-testid="error-display"
        />
      );

      const dismissButton = screen.getByText('닫기');
      fireEvent.click(dismissButton);

      expect(dismissMock).toHaveBeenCalledTimes(1);
    });

    it('should render in compact mode', () => {
      const networkError = ChatErrorHandler.processError(new Error('Failed to fetch'));
      
      render(
        <ChatErrorDisplay
          error={networkError}
          compact={true}
          data-testid="error-display"
        />
      );

      // In compact mode, should still show essential information
      expect(screen.getByText('연결 오류')).toBeInTheDocument();
      expect(screen.getByText('다시 시도')).toBeInTheDocument();
    });

    it('should show technical details in development mode', () => {
      // Mock development environment
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      const error = ChatErrorHandler.processError(new Error('Test error'), {
        endpoint: '/api/test'
      });
      
      render(
        <ChatErrorDisplay
          error={error}
          data-testid="error-display"
        />
      );

      // Should show details toggle in development
      expect(screen.getByText('기술적 세부사항')).toBeInTheDocument();

      // Restore environment
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('ChatErrorToast Component', () => {
    it('should auto-hide after specified delay', async () => {
      const dismissMock = vi.fn();
      const networkError = ChatErrorHandler.processError(new Error('Failed to fetch'));
      
      render(
        <ChatErrorToast
          error={networkError}
          onDismiss={dismissMock}
          autoHide={true}
          hideDelay={100} // Short delay for testing
        />
      );

      // Should be visible initially
      expect(screen.getByText('연결 오류')).toBeInTheDocument();

      // Should auto-dismiss after delay
      await waitFor(() => {
        expect(dismissMock).toHaveBeenCalledTimes(1);
      }, { timeout: 200 });
    });

    it('should not auto-hide when autoHide is false', async () => {
      const dismissMock = vi.fn();
      const networkError = ChatErrorHandler.processError(new Error('Failed to fetch'));
      
      render(
        <ChatErrorToast
          error={networkError}
          onDismiss={dismissMock}
          autoHide={false}
        />
      );

      // Wait a bit to ensure it doesn't auto-dismiss
      await waitFor(() => {
        // Just check that the component is still rendered
        expect(screen.getByText('연결 오류')).toBeInTheDocument();
      }, { timeout: 150 });
      
      expect(dismissMock).not.toHaveBeenCalled();
    });
  });

  describe('useChatErrorHandler Hook', () => {
    it('should handle errors and provide state', () => {
      const onErrorMock = vi.fn();
      let errorHandler: any;

      const TestComponent = () => {
        errorHandler = useChatErrorHandler({
          onError: onErrorMock
        });
        
        return (
          <div>
            <button 
              onClick={() => errorHandler.handleError(new Error('Test error'))}
              data-testid="trigger-error"
            >
              Trigger Error
            </button>
            {errorHandler.isShowingError && (
              <div data-testid="error-showing">Error is showing</div>
            )}
          </div>
        );
      };

      render(<TestComponent />);

      const triggerButton = screen.getByTestId('trigger-error');
      fireEvent.click(triggerButton);

      expect(onErrorMock).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId('error-showing')).toBeInTheDocument();
    });

    it('should clear errors', () => {
      let errorHandler: any;

      const TestComponent = () => {
        errorHandler = useChatErrorHandler();
        
        return (
          <div>
            <button 
              onClick={() => errorHandler.handleError(new Error('Test error'))}
              data-testid="trigger-error"
            >
              Trigger Error
            </button>
            <button 
              onClick={() => errorHandler.clearError()}
              data-testid="clear-error"
            >
              Clear Error
            </button>
            {errorHandler.isShowingError && (
              <div data-testid="error-showing">Error is showing</div>
            )}
          </div>
        );
      };

      render(<TestComponent />);

      // Trigger error
      fireEvent.click(screen.getByTestId('trigger-error'));
      expect(screen.getByTestId('error-showing')).toBeInTheDocument();

      // Clear error
      fireEvent.click(screen.getByTestId('clear-error'));
      expect(screen.queryByTestId('error-showing')).not.toBeInTheDocument();
    });

    it('should handle retry functionality', () => {
      const onRetryMock = vi.fn();
      let errorHandler: any;

      const TestComponent = () => {
        errorHandler = useChatErrorHandler({
          onRetry: onRetryMock
        });
        
        return (
          <div>
            <button 
              onClick={() => errorHandler.handleError(new Error('Test error'))}
              data-testid="trigger-error"
            >
              Trigger Error
            </button>
            <button 
              onClick={() => errorHandler.retryLastAction()}
              data-testid="retry-action"
            >
              Retry
            </button>
          </div>
        );
      };

      render(<TestComponent />);

      // Trigger error then retry
      fireEvent.click(screen.getByTestId('trigger-error'));
      fireEvent.click(screen.getByTestId('retry-action'));

      expect(onRetryMock).toHaveBeenCalledTimes(1);
    });
  });

  describe('Integration with Chat System', () => {
    it('should handle chat errors end-to-end', async () => {
      const retryMock = vi.fn();
      const networkError = new Error('Failed to fetch');
      
      render(
        <TestErrorComponent 
          error={networkError}
          onRetry={retryMock}
        />
      );

      // Should show error display
      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toBeInTheDocument();
      });

      // Should show network error message
      expect(screen.getByText('연결 오류')).toBeInTheDocument();
      expect(screen.getByText(/네트워크 연결에 문제가 있습니다/)).toBeInTheDocument();

      // Should handle retry
      const retryButton = screen.getByText('다시 시도');
      fireEvent.click(retryButton);

      expect(retryMock).toHaveBeenCalledTimes(1);
    });

    it('should handle authentication errors with login redirect', () => {
      const authError = {
        status: 401,
        type: 'auth_error',
        message: 'Unauthorized'
      };
      
      // Mock window.location
      const mockLocation = {
        href: '',
        pathname: '/chat'
      };
      Object.defineProperty(window, 'location', {
        value: mockLocation,
        writable: true
      });

      render(<TestErrorComponent error={authError} />);

      expect(screen.getByText('인증 오류')).toBeInTheDocument();
      expect(screen.getByText('로그인하기')).toBeInTheDocument();

      // Click login button
      const loginButton = screen.getByText('로그인하기');
      fireEvent.click(loginButton);

      // Should redirect to login page
      expect(mockLocation.href).toContain('/login');
      expect(mockLocation.href).toContain('returnTo=%2Fchat');
    });
  });
});