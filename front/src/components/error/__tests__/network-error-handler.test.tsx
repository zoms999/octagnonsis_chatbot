import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import NetworkErrorHandler, { useNetworkErrorHandler } from '../network-error-handler';
import { renderHook, act } from '@testing-library/react';

// Mock timers
beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

const mockNetworkError = {
  status: 0,
  message: 'Network connection failed',
  type: 'network_error' as const,
  code: 'NETWORK_ERROR',
};

const mockTimeoutError = {
  status: 0,
  message: 'Request timed out',
  type: 'network_error' as const,
  code: 'TIMEOUT_ERROR',
};

describe('NetworkErrorHandler', () => {
  it('renders network error message', () => {
    render(
      <NetworkErrorHandler error={mockNetworkError} />
    );

    expect(screen.getByText('Connection Error')).toBeInTheDocument();
    expect(screen.getByText(/Unable to connect to the server/)).toBeInTheDocument();
  });

  it('renders timeout error with appropriate icon and message', () => {
    render(
      <NetworkErrorHandler error={mockTimeoutError} />
    );

    expect(screen.getByText('Request Timeout')).toBeInTheDocument();
    expect(screen.getByText(/The request timed out/)).toBeInTheDocument();
  });

  it('shows retry button when onRetry is provided', () => {
    const onRetry = vi.fn();
    
    render(
      <NetworkErrorHandler error={mockNetworkError} onRetry={onRetry} />
    );

    const retryButton = screen.getByRole('button', { name: 'Retry' });
    expect(retryButton).toBeInTheDocument();
    expect(retryButton).toBeEnabled();
  });

  it('calls onRetry when retry button is clicked', () => {
    const onRetry = vi.fn();
    
    render(
      <NetworkErrorHandler error={mockNetworkError} onRetry={onRetry} />
    );

    const retryButton = screen.getByRole('button', { name: 'Retry' });
    fireEvent.click(retryButton);

    expect(onRetry).toHaveBeenCalled();
  });

  it('shows dismiss button when onDismiss is provided', () => {
    const onDismiss = vi.fn();
    
    render(
      <NetworkErrorHandler error={mockNetworkError} onDismiss={onDismiss} />
    );

    const dismissButton = screen.getByRole('button', { name: 'Dismiss' });
    fireEvent.click(dismissButton);

    expect(onDismiss).toHaveBeenCalled();
  });

  it('performs auto-retry when enabled', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    
    render(
      <NetworkErrorHandler 
        error={mockNetworkError} 
        onRetry={onRetry}
        autoRetry={true}
        maxRetries={2}
        retryDelay={1000}
      />
    );

    // Should start first retry after delay
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  it('shows retry count during auto-retry', async () => {
    const onRetry = vi.fn().mockRejectedValue(mockNetworkError);
    
    render(
      <NetworkErrorHandler 
        error={mockNetworkError} 
        onRetry={onRetry}
        autoRetry={true}
        maxRetries={3}
        retryDelay={1000}
      />
    );

    // First retry
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(screen.getByText('Retry attempt 1 of 3')).toBeInTheDocument();
    });
  });

  it('shows countdown for next retry', async () => {
    const onRetry = vi.fn().mockRejectedValue(mockNetworkError);
    
    render(
      <NetworkErrorHandler 
        error={mockNetworkError} 
        onRetry={onRetry}
        autoRetry={true}
        maxRetries={2}
        retryDelay={2000}
      />
    );

    // Should show countdown
    expect(screen.getByText(/Retrying automatically in 2 seconds/)).toBeInTheDocument();

    // Advance by 1 second
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(screen.getByText(/Retrying automatically in 1 seconds/)).toBeInTheDocument();
    });
  });

  it('disables retry button during auto-retry', () => {
    const onRetry = vi.fn();
    
    render(
      <NetworkErrorHandler 
        error={mockNetworkError} 
        onRetry={onRetry}
        autoRetry={true}
        maxRetries={2}
      />
    );

    const retryButton = screen.getByRole('button', { name: 'Retry' });
    expect(retryButton).toBeDisabled();
  });

  it('shows max retries reached message', async () => {
    const onRetry = vi.fn().mockRejectedValue(mockNetworkError);
    
    render(
      <NetworkErrorHandler 
        error={mockNetworkError} 
        onRetry={onRetry}
        autoRetry={true}
        maxRetries={1}
        retryDelay={100}
      />
    );

    // Wait for retry to complete
    act(() => {
      vi.advanceTimersByTime(200);
    });

    await waitFor(() => {
      expect(screen.getByText(/Maximum retry attempts reached/)).toBeInTheDocument();
    });
  });

  it('shows retrying indicator during retry', async () => {
    const onRetry = vi.fn().mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)));
    
    render(
      <NetworkErrorHandler 
        error={mockNetworkError} 
        onRetry={onRetry}
      />
    );

    const retryButton = screen.getByRole('button', { name: 'Retry' });
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText('Retrying...')).toBeInTheDocument();
    });
  });

  it('uses exponential backoff for retry delays', async () => {
    const onRetry = vi.fn().mockRejectedValue(mockNetworkError);
    
    render(
      <NetworkErrorHandler 
        error={mockNetworkError} 
        onRetry={onRetry}
        autoRetry={true}
        maxRetries={3}
        retryDelay={1000}
      />
    );

    // First retry after 1000ms
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    // Second retry after 2000ms (exponential backoff)
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    await waitFor(() => {
      expect(onRetry).toHaveBeenCalledTimes(2);
    });
  });

  it('provides user-friendly messages for different error codes', () => {
    const corsError = {
      status: 0,
      message: 'CORS error',
      type: 'network_error' as const,
      code: 'CORS_ERROR',
    };

    render(<NetworkErrorHandler error={corsError} />);

    expect(screen.getByText(/Cross-origin request blocked/)).toBeInTheDocument();
  });
});

describe('useNetworkErrorHandler', () => {
  beforeEach(() => {
    // Mock navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true,
    });
  });

  it('initializes with correct default state', () => {
    const { result } = renderHook(() => useNetworkErrorHandler());

    expect(result.current.isOffline).toBe(false);
    expect(result.current.hasNetworkError).toBe(false);
    expect(result.current.isConnected()).toBe(true);
  });

  it('handles network error correctly', () => {
    const { result } = renderHook(() => useNetworkErrorHandler());

    act(() => {
      result.current.handleNetworkError(mockNetworkError);
    });

    expect(result.current.hasNetworkError).toBe(true);
    expect(result.current.error).toEqual(mockNetworkError);
  });

  it('ignores non-network errors', () => {
    const { result } = renderHook(() => useNetworkErrorHandler());

    const serverError = {
      status: 500,
      message: 'Server error',
      type: 'server_error',
    };

    act(() => {
      result.current.handleNetworkError(serverError);
    });

    expect(result.current.hasNetworkError).toBe(false);
  });

  it('tracks online/offline status', () => {
    const { result } = renderHook(() => useNetworkErrorHandler());

    // Simulate going offline
    Object.defineProperty(navigator, 'onLine', { value: false });
    act(() => {
      window.dispatchEvent(new Event('offline'));
    });

    expect(result.current.isOffline).toBe(true);
    expect(result.current.isConnected()).toBe(false);

    // Simulate going online
    Object.defineProperty(navigator, 'onLine', { value: true });
    act(() => {
      window.dispatchEvent(new Event('online'));
    });

    expect(result.current.isOffline).toBe(false);
    expect(result.current.isConnected()).toBe(true);
  });

  it('retries operation with exponential backoff', async () => {
    const { result } = renderHook(() => useNetworkErrorHandler({ maxRetries: 2, retryDelay: 100 }));

    let attemptCount = 0;
    const operation = vi.fn().mockImplementation(() => {
      attemptCount++;
      if (attemptCount < 3) {
        throw mockNetworkError;
      }
      return 'success';
    });

    const promise = act(async () => {
      return result.current.retryOperation(operation);
    });

    // Advance timers to complete retries
    act(() => {
      vi.advanceTimersByTime(500);
    });

    const resultValue = await promise;
    expect(resultValue).toBe('success');
    expect(operation).toHaveBeenCalledTimes(3);
  });

  it('does not retry non-network errors', async () => {
    const { result } = renderHook(() => useNetworkErrorHandler());

    const authError = {
      status: 401,
      message: 'Unauthorized',
      type: 'auth_error',
    };

    const operation = vi.fn().mockRejectedValue(authError);

    await expect(
      act(async () => {
        return result.current.retryOperation(operation);
      })
    ).rejects.toEqual(authError);

    expect(operation).toHaveBeenCalledTimes(1);
  });

  it('clears network error state on successful retry', async () => {
    const { result } = renderHook(() => useNetworkErrorHandler());

    // Set initial error state
    act(() => {
      result.current.handleNetworkError(mockNetworkError);
    });

    expect(result.current.hasNetworkError).toBe(true);

    // Successful operation should clear error
    const operation = vi.fn().mockResolvedValue('success');

    await act(async () => {
      return result.current.retryOperation(operation);
    });

    expect(result.current.hasNetworkError).toBe(false);
    expect(result.current.error).toBeUndefined();
  });

  it('can manually clear network error', () => {
    const { result } = renderHook(() => useNetworkErrorHandler());

    act(() => {
      result.current.handleNetworkError(mockNetworkError);
    });

    expect(result.current.hasNetworkError).toBe(true);

    act(() => {
      result.current.clearNetworkError();
    });

    expect(result.current.hasNetworkError).toBe(false);
    expect(result.current.error).toBeUndefined();
  });
});