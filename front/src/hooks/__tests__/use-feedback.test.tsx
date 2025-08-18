import { renderHook, act, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFeedback } from '../use-feedback';
import { ApiClient } from '@/lib/api';

// Mock ApiClient
vi.mock('@/lib/api', () => ({
  ApiClient: {
    submitFeedback: vi.fn(),
  },
}));

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

describe('useFeedback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with correct default state', () => {
    const { result } = renderHook(() => useFeedback(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isSubmitting).toBe(false);
    expect(result.current.error).toBe(null);
    expect(result.current.isSuccess).toBe(false);
    expect(result.current.hasFeedback('test-message')).toBe(false);
  });

  it('submits feedback successfully', async () => {
    const mockResponse = { feedback_id: 'feedback-123', message: 'Success' };
    vi.mocked(ApiClient.submitFeedback).mockResolvedValue(mockResponse);
    
    const onSuccess = vi.fn();
    const { result } = renderHook(() => useFeedback({ onSuccess }), {
      wrapper: createWrapper(),
    });

    const feedback = {
      conversation_id: 'conv-123',
      message_id: 'msg-123',
      feedback_type: 'helpful' as const,
    };

    act(() => {
      result.current.submitFeedback(feedback);
    });

    expect(result.current.isSubmitting).toBe(true);

    await waitFor(() => {
      expect(result.current.isSubmitting).toBe(false);
    });

    expect(ApiClient.submitFeedback).toHaveBeenCalledWith(feedback);
    expect(onSuccess).toHaveBeenCalledWith(mockResponse);
    expect(result.current.isSuccess).toBe(true);
    expect(result.current.hasFeedback('msg-123')).toBe(true);
  });

  it('handles feedback submission error', async () => {
    const mockError = new Error('Submission failed');
    vi.mocked(ApiClient.submitFeedback).mockRejectedValue(mockError);
    
    const onError = vi.fn();
    const { result } = renderHook(() => useFeedback({ onError }), {
      wrapper: createWrapper(),
    });

    const feedback = {
      conversation_id: 'conv-123',
      message_id: 'msg-123',
      feedback_type: 'helpful' as const,
    };

    act(() => {
      result.current.submitFeedback(feedback);
    });

    await waitFor(() => {
      expect(result.current.isSubmitting).toBe(false);
    });

    expect(onError).toHaveBeenCalledWith(mockError);
    expect(result.current.error).toBe(mockError);
    expect(result.current.hasFeedback('msg-123')).toBe(false);
  });

  it('tracks multiple feedback submissions', async () => {
    const mockResponse = { feedback_id: 'feedback-123', message: 'Success' };
    vi.mocked(ApiClient.submitFeedback).mockResolvedValue(mockResponse);
    
    const { result } = renderHook(() => useFeedback(), {
      wrapper: createWrapper(),
    });

    // Submit feedback for first message
    act(() => {
      result.current.submitFeedback({
        conversation_id: 'conv-123',
        message_id: 'msg-1',
        feedback_type: 'helpful',
      });
    });

    await waitFor(() => {
      expect(result.current.hasFeedback('msg-1')).toBe(true);
    });

    // Submit feedback for second message
    act(() => {
      result.current.submitFeedback({
        conversation_id: 'conv-123',
        message_id: 'msg-2',
        feedback_type: 'not_helpful',
      });
    });

    await waitFor(() => {
      expect(result.current.hasFeedback('msg-2')).toBe(true);
    });

    // Both messages should have feedback
    expect(result.current.hasFeedback('msg-1')).toBe(true);
    expect(result.current.hasFeedback('msg-2')).toBe(true);
    expect(result.current.hasFeedback('msg-3')).toBe(false);
  });

  it('handles feedback with rating and comments', async () => {
    const mockResponse = { feedback_id: 'feedback-123', message: 'Success' };
    vi.mocked(ApiClient.submitFeedback).mockResolvedValue(mockResponse);
    
    const { result } = renderHook(() => useFeedback(), {
      wrapper: createWrapper(),
    });

    const feedback = {
      conversation_id: 'conv-123',
      message_id: 'msg-123',
      feedback_type: 'rating' as const,
      rating: 4,
      comments: 'Very helpful response!',
    };

    act(() => {
      result.current.submitFeedback(feedback);
    });

    await waitFor(() => {
      expect(result.current.isSubmitting).toBe(false);
    });

    expect(ApiClient.submitFeedback).toHaveBeenCalledWith(feedback);
    expect(result.current.hasFeedback('msg-123')).toBe(true);
  });
});