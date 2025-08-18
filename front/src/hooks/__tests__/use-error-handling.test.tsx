import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import useErrorHandling, { useFormErrorHandling, useAsyncOperation } from '../use-error-handling';
import { useToast } from '@/providers/toast-provider';
import { useAuth } from '@/providers/auth-provider';

// Mock dependencies
vi.mock('next/navigation');
vi.mock('@/providers/toast-provider');
vi.mock('@/providers/auth-provider');

const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
  prefetch: vi.fn(),
};

const mockToast = {
  showError: vi.fn(),
  showSuccess: vi.fn(),
  showWarning: vi.fn(),
  showInfo: vi.fn(),
  addToast: vi.fn(),
  removeToast: vi.fn(),
  clearAll: vi.fn(),
};

const mockAuth = {
  user: null,
  login: vi.fn(),
  logout: vi.fn(),
  isLoading: false,
  isAuthenticated: false,
};

beforeEach(() => {
  vi.mocked(useRouter).mockReturnValue(mockRouter);
  vi.mocked(useToast).mockReturnValue(mockToast);
  vi.mocked(useAuth).mockReturnValue(mockAuth);
  
  // Clear all mocks
  vi.clearAllMocks();
  
  // Mock console.error
  console.error = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('useErrorHandling', () => {
  it('handles authentication errors correctly', () => {
    const { result } = renderHook(() => useErrorHandling(), {
      wrapper: createWrapper(),
    });

    const authError = {
      status: 401,
      message: 'Unauthorized',
      type: 'auth_error',
    };

    act(() => {
      result.current.handleError(authError, 'Test context');
    });

    expect(mockAuth.logout).toHaveBeenCalled();
    expect(mockRouter.push).toHaveBeenCalledWith('/login');
    expect(mockToast.showError).toHaveBeenCalledWith(authError, 'Test context');
  });

  it('handles rate limit errors with warning', () => {
    const { result } = renderHook(() => useErrorHandling(), {
      wrapper: createWrapper(),
    });

    const rateLimitError = {
      status: 429,
      message: 'Too Many Requests',
      type: 'rate_limit_error',
      retry_after: 60,
    };

    act(() => {
      result.current.handleError(rateLimitError, 'Test context');
    });

    expect(mockToast.showWarning).toHaveBeenCalledWith(
      'Too many requests. Please wait 60 seconds before trying again.',
      'Rate Limited'
    );
  });

  it('handles network errors', () => {
    const { result } = renderHook(() => useErrorHandling(), {
      wrapper: createWrapper(),
    });

    const networkError = {
      status: 0,
      message: 'Network Error',
      type: 'network_error',
    };

    act(() => {
      result.current.handleError(networkError, 'Test context');
    });

    expect(mockToast.showError).toHaveBeenCalledWith(networkError, 'Test context');
  });

  it('handles validation errors', () => {
    const { result } = renderHook(() => useErrorHandling(), {
      wrapper: createWrapper(),
    });

    const validationError = {
      status: 400,
      message: 'Validation Error',
      type: 'validation_error',
      field_errors: {
        username: ['This field is required'],
      },
    };

    act(() => {
      result.current.handleError(validationError, 'Test context');
    });

    expect(mockToast.showError).toHaveBeenCalledWith(validationError, 'Test context');
  });

  it('handles server errors', () => {
    const { result } = renderHook(() => useErrorHandling(), {
      wrapper: createWrapper(),
    });

    const serverError = {
      status: 500,
      message: 'Internal Server Error',
      type: 'server_error',
    };

    act(() => {
      result.current.handleError(serverError, 'Test context');
    });

    expect(mockToast.showError).toHaveBeenCalledWith(serverError, 'Test context');
  });

  it('respects showToast option', () => {
    const { result } = renderHook(() => useErrorHandling({ showToast: false }), {
      wrapper: createWrapper(),
    });

    const error = {
      status: 500,
      message: 'Server Error',
      type: 'server_error',
    };

    act(() => {
      result.current.handleError(error, 'Test context');
    });

    expect(mockToast.showError).not.toHaveBeenCalled();
  });

  it('respects redirectOnAuth option', () => {
    const { result } = renderHook(() => useErrorHandling({ redirectOnAuth: false }), {
      wrapper: createWrapper(),
    });

    const authError = {
      status: 401,
      message: 'Unauthorized',
      type: 'auth_error',
    };

    act(() => {
      result.current.handleError(authError, 'Test context');
    });

    expect(mockRouter.push).not.toHaveBeenCalled();
  });

  it('retries operations with exponential backoff', async () => {
    const { result } = renderHook(() => useErrorHandling(), {
      wrapper: createWrapper(),
    });

    let attemptCount = 0;
    const operation = vi.fn().mockImplementation(() => {
      attemptCount++;
      if (attemptCount < 3) {
        throw new Error('Temporary error');
      }
      return 'success';
    });

    const resultValue = await act(async () => {
      return result.current.retryOperation(operation, 3, 10);
    });

    expect(resultValue).toBe('success');
    expect(operation).toHaveBeenCalledTimes(3);
  });

  it('does not retry auth errors', async () => {
    const { result } = renderHook(() => useErrorHandling(), {
      wrapper: createWrapper(),
    });

    const operation = vi.fn().mockRejectedValue({
      status: 401,
      message: 'Unauthorized',
      type: 'auth_error',
    });

    await expect(
      act(async () => {
        return result.current.retryOperation(operation, 3, 10);
      })
    ).rejects.toMatchObject({
      status: 401,
      type: 'auth_error',
    });

    expect(operation).toHaveBeenCalledTimes(1);
  });

  it('checks if error is retryable', () => {
    const { result } = renderHook(() => useErrorHandling(), {
      wrapper: createWrapper(),
    });

    const networkError = { status: 0, type: 'network_error' };
    const authError = { status: 401, type: 'auth_error' };

    expect(result.current.isRetryable(networkError)).toBe(true);
    expect(result.current.isRetryable(authError)).toBe(false);
  });

  it('gets retry delay for rate limit errors', () => {
    const { result } = renderHook(() => useErrorHandling(), {
      wrapper: createWrapper(),
    });

    const rateLimitError = {
      status: 429,
      type: 'rate_limit_error',
      retry_after: 120,
    };

    const delay = result.current.getRetryDelay(rateLimitError);
    expect(delay).toBe(120000); // 120 seconds in milliseconds
  });
});

describe('useFormErrorHandling', () => {
  it('extracts field errors from validation error', () => {
    const { result } = renderHook(() => useFormErrorHandling(), {
      wrapper: createWrapper(),
    });

    const validationError = {
      status: 400,
      message: 'Validation Error',
      type: 'validation_error',
      field_errors: {
        username: ['Username is required'],
        email: ['Invalid email format'],
      },
    };

    const fieldErrors = act(() => {
      return result.current.handleFormError(validationError);
    });

    expect(fieldErrors).toEqual({
      username: 'Username is required',
      email: 'Invalid email format',
    });
  });

  it('handles array of error messages', () => {
    const { result } = renderHook(() => useFormErrorHandling(), {
      wrapper: createWrapper(),
    });

    const validationError = {
      status: 400,
      message: 'Validation Error',
      type: 'validation_error',
      field_errors: {
        password: ['Password too short', 'Password must contain numbers'],
      },
    };

    const fieldErrors = act(() => {
      return result.current.handleFormError(validationError);
    });

    expect(fieldErrors).toEqual({
      password: 'Password too short', // Should take first error
    });
  });

  it('returns empty object for non-validation errors', () => {
    const { result } = renderHook(() => useFormErrorHandling(), {
      wrapper: createWrapper(),
    });

    const serverError = {
      status: 500,
      message: 'Server Error',
      type: 'server_error',
    };

    const fieldErrors = act(() => {
      return result.current.handleFormError(serverError);
    });

    expect(fieldErrors).toEqual({});
  });
});

describe('useAsyncOperation', () => {
  it('executes operation successfully', async () => {
    const { result } = renderHook(() => useAsyncOperation(), {
      wrapper: createWrapper(),
    });

    const operation = vi.fn().mockResolvedValue('success');
    const onSuccess = vi.fn();

    const resultValue = await act(async () => {
      return result.current.executeAsync(operation, { onSuccess });
    });

    expect(resultValue).toBe('success');
    expect(onSuccess).toHaveBeenCalledWith('success');
  });

  it('handles operation failure', async () => {
    const { result } = renderHook(() => useAsyncOperation(), {
      wrapper: createWrapper(),
    });

    const error = new Error('Operation failed');
    const operation = vi.fn().mockRejectedValue(error);
    const onError = vi.fn();

    const resultValue = await act(async () => {
      return result.current.executeAsync(operation, { onError });
    });

    expect(resultValue).toBeNull();
    expect(onError).toHaveBeenCalledWith(error);
  });

  it('shows success toast when enabled', async () => {
    // Mock window.dispatchEvent
    const dispatchEvent = vi.fn();
    Object.defineProperty(window, 'dispatchEvent', {
      value: dispatchEvent,
      writable: true,
    });

    const { result } = renderHook(() => useAsyncOperation(), {
      wrapper: createWrapper(),
    });

    const operation = vi.fn().mockResolvedValue('success');

    await act(async () => {
      return result.current.executeAsync(operation, {
        showSuccessToast: true,
        successMessage: 'Operation completed',
      });
    });

    expect(dispatchEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'global:success',
        detail: { message: 'Operation completed' },
      })
    );
  });

  it('retries operation when specified', async () => {
    const { result } = renderHook(() => useAsyncOperation(), {
      wrapper: createWrapper(),
    });

    let attemptCount = 0;
    const operation = vi.fn().mockImplementation(() => {
      attemptCount++;
      if (attemptCount < 2) {
        throw new Error('Temporary error');
      }
      return 'success';
    });

    const resultValue = await act(async () => {
      return result.current.executeAsync(operation, { retries: 2 });
    });

    expect(resultValue).toBe('success');
    expect(operation).toHaveBeenCalledTimes(2);
  });
});