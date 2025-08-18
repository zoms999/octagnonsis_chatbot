import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import RateLimitHandler, { useRateLimitHandler } from '../rate-limit-handler';
import { renderHook, act } from '@testing-library/react';

// Mock timers
beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

const mockRateLimitError = {
  status: 429,
  message: 'Too many requests',
  type: 'rate_limit' as const,
  retry_after: 60,
};

describe('RateLimitHandler', () => {
  it('renders rate limit message', () => {
    render(
      <RateLimitHandler error={mockRateLimitError} />
    );

    expect(screen.getByText('Rate Limit Exceeded')).toBeInTheDocument();
    expect(screen.getByText('Too many requests')).toBeInTheDocument();
  });

  it('shows countdown timer when showCountdown is true', () => {
    render(
      <RateLimitHandler error={mockRateLimitError} showCountdown={true} />
    );

    expect(screen.getByText(/Please wait 1m 0s before retrying/)).toBeInTheDocument();
  });

  it('updates countdown every second', async () => {
    render(
      <RateLimitHandler error={mockRateLimitError} showCountdown={true} />
    );

    expect(screen.getByText(/Please wait 1m 0s before retrying/)).toBeInTheDocument();

    // Advance timer by 1 second
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(screen.getByText(/Please wait 59s before retrying/)).toBeInTheDocument();
    });
  });

  it('enables retry button when countdown reaches zero', async () => {
    render(
      <RateLimitHandler 
        error={mockRateLimitError} 
        showCountdown={true}
        onRetry={vi.fn()}
      />
    );

    const retryButton = screen.getByRole('button', { name: /Retry in/ });
    expect(retryButton).toBeDisabled();

    // Advance timer to completion
    act(() => {
      vi.advanceTimersByTime(60000);
    });

    await waitFor(() => {
      const enabledRetryButton = screen.getByRole('button', { name: 'Retry Now' });
      expect(enabledRetryButton).toBeEnabled();
    });
  });

  it('calls onRetry when retry button is clicked after countdown', async () => {
    const onRetry = vi.fn();
    
    render(
      <RateLimitHandler 
        error={mockRateLimitError} 
        showCountdown={true}
        onRetry={onRetry}
      />
    );

    // Advance timer to completion
    act(() => {
      vi.advanceTimersByTime(60000);
    });

    await waitFor(() => {
      const retryButton = screen.getByRole('button', { name: 'Retry Now' });
      fireEvent.click(retryButton);
    });

    expect(onRetry).toHaveBeenCalled();
  });

  it('calls onDismiss when dismiss button is clicked', () => {
    const onDismiss = vi.fn();
    
    render(
      <RateLimitHandler 
        error={mockRateLimitError} 
        onDismiss={onDismiss}
      />
    );

    const dismissButton = screen.getByRole('button', { name: 'Dismiss' });
    fireEvent.click(dismissButton);

    expect(onDismiss).toHaveBeenCalled();
  });

  it('shows progress bar during countdown', () => {
    render(
      <RateLimitHandler error={mockRateLimitError} showCountdown={true} />
    );

    const progressBar = screen.getByRole('progressbar', { hidden: true });
    expect(progressBar).toBeInTheDocument();
  });

  it('formats time correctly for different durations', () => {
    const shortError = { ...mockRateLimitError, retry_after: 30 };
    const { rerender } = render(
      <RateLimitHandler error={shortError} showCountdown={true} />
    );

    expect(screen.getByText(/Please wait 30s before retrying/)).toBeInTheDocument();

    const longError = { ...mockRateLimitError, retry_after: 150 };
    rerender(<RateLimitHandler error={longError} showCountdown={true} />);

    expect(screen.getByText(/Please wait 2m 30s before retrying/)).toBeInTheDocument();
  });

  it('does not show countdown when showCountdown is false', () => {
    render(
      <RateLimitHandler error={mockRateLimitError} showCountdown={false} />
    );

    expect(screen.queryByText(/Please wait/)).not.toBeInTheDocument();
  });

  it('uses default retry_after when not provided', () => {
    const errorWithoutRetryAfter = {
      status: 429,
      message: 'Too many requests',
      type: 'rate_limit' as const,
    };

    render(
      <RateLimitHandler error={errorWithoutRetryAfter} showCountdown={true} />
    );

    expect(screen.getByText(/Please wait 1m 0s before retrying/)).toBeInTheDocument();
  });
});

describe('useRateLimitHandler', () => {
  it('initializes with not rate limited state', () => {
    const { result } = renderHook(() => useRateLimitHandler());

    expect(result.current.isRateLimited).toBe(false);
    expect(result.current.canRetry()).toBe(true);
  });

  it('handles rate limit error correctly', () => {
    const { result } = renderHook(() => useRateLimitHandler());

    act(() => {
      result.current.handleRateLimitError(mockRateLimitError);
    });

    expect(result.current.isRateLimited).toBe(true);
    expect(result.current.error).toEqual(mockRateLimitError);
    expect(result.current.retryAfter).toBe(60);
    expect(result.current.canRetry()).toBe(false);
  });

  it('ignores non-rate-limit errors', () => {
    const { result } = renderHook(() => useRateLimitHandler());

    const nonRateLimitError = {
      status: 500,
      message: 'Server error',
      type: 'server_error',
    };

    act(() => {
      result.current.handleRateLimitError(nonRateLimitError);
    });

    expect(result.current.isRateLimited).toBe(false);
  });

  it('auto-clears rate limit after retry period', async () => {
    const { result } = renderHook(() => useRateLimitHandler());

    act(() => {
      result.current.handleRateLimitError(mockRateLimitError);
    });

    expect(result.current.isRateLimited).toBe(true);

    // Advance timer past retry period
    act(() => {
      vi.advanceTimersByTime(60000);
    });

    await waitFor(() => {
      expect(result.current.isRateLimited).toBe(false);
    });
  });

  it('can manually clear rate limit', () => {
    const { result } = renderHook(() => useRateLimitHandler());

    act(() => {
      result.current.handleRateLimitError(mockRateLimitError);
    });

    expect(result.current.isRateLimited).toBe(true);

    act(() => {
      result.current.clearRateLimit();
    });

    expect(result.current.isRateLimited).toBe(false);
  });

  it('uses default retry_after when not provided', () => {
    const { result } = renderHook(() => useRateLimitHandler());

    const errorWithoutRetryAfter = {
      status: 429,
      message: 'Too many requests',
      type: 'rate_limit' as const,
    };

    act(() => {
      result.current.handleRateLimitError(errorWithoutRetryAfter);
    });

    expect(result.current.retryAfter).toBe(60);
  });
});