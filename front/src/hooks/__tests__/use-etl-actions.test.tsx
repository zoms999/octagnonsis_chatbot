import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useETLActions } from '../use-etl-actions';
import { useRetryETLJob, useCancelETLJob, useTriggerReprocessing } from '../api-hooks';
import { useToast } from '@/components/ui/toast';
import { ETLJob } from '@/lib/types';

// Mock dependencies
vi.mock('../api-hooks');
vi.mock('@/components/ui/toast');

const mockToast = vi.fn();
const mockRetryMutation = {
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
};
const mockCancelMutation = {
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
};
const mockReprocessMutation = {
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
};

function createWrapper() {
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
}

const mockFailedJob: ETLJob = {
  job_id: 'job-123',
  status: 'failed',
  progress: 0,
  current_step: 'Failed step',
  error_message: 'Test error',
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T10:30:00Z',
};

const mockRunningJob: ETLJob = {
  job_id: 'job-456',
  status: 'running',
  progress: 50,
  current_step: 'Processing',
  created_at: '2024-01-01T11:00:00Z',
  updated_at: '2024-01-01T11:15:00Z',
};

describe('useETLActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useToast as any).mockReturnValue({ toast: mockToast });
    (useRetryETLJob as any).mockReturnValue(mockRetryMutation);
    (useCancelETLJob as any).mockReturnValue(mockCancelMutation);
    (useTriggerReprocessing as any).mockReturnValue(mockReprocessMutation);
  });

  it('should initialize with empty state', () => {
    const { result } = renderHook(() => useETLActions(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isRetrying('any-job')).toBe(false);
    expect(result.current.isCancelling('any-job')).toBe(false);
    expect(result.current.isReprocessing('any-user')).toBe(false);
    expect(result.current.isAnyActionLoading).toBe(false);
  });

  describe('canRetryJob', () => {
    it('should return true for failed jobs', () => {
      const { result } = renderHook(() => useETLActions(), {
        wrapper: createWrapper(),
      });

      expect(result.current.canRetryJob(mockFailedJob)).toBe(true);
    });

    it('should return false for running jobs', () => {
      const { result } = renderHook(() => useETLActions(), {
        wrapper: createWrapper(),
      });

      expect(result.current.canRetryJob(mockRunningJob)).toBe(false);
    });
  });

  describe('canCancelJob', () => {
    it('should return true for running jobs', () => {
      const { result } = renderHook(() => useETLActions(), {
        wrapper: createWrapper(),
      });

      expect(result.current.canCancelJob(mockRunningJob)).toBe(true);
    });

    it('should return false for failed jobs', () => {
      const { result } = renderHook(() => useETLActions(), {
        wrapper: createWrapper(),
      });

      expect(result.current.canCancelJob(mockFailedJob)).toBe(false);
    });
  });

  describe('retryJob', () => {
    it('should call retry mutation and update state', () => {
      const { result } = renderHook(() => useETLActions(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.retryJob('job-123');
      });

      expect(mockRetryMutation.mutate).toHaveBeenCalledWith('job-123');
      expect(result.current.isRetrying('job-123')).toBe(true);
    });
  });

  describe('cancelJob', () => {
    it('should call cancel mutation and update state', () => {
      const { result } = renderHook(() => useETLActions(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.cancelJob('job-456');
      });

      expect(mockCancelMutation.mutate).toHaveBeenCalledWith('job-456');
      expect(result.current.isCancelling('job-456')).toBe(true);
    });
  });

  describe('triggerReprocessing', () => {
    it('should call reprocessing mutation with correct parameters', () => {
      const { result } = renderHook(() => useETLActions(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.triggerReprocessing('user-123', true);
      });

      expect(mockReprocessMutation.mutate).toHaveBeenCalledWith({
        userId: 'user-123',
        force: true,
      });
      expect(result.current.isReprocessing('user-123')).toBe(true);
    });

    it('should default force parameter to false', () => {
      const { result } = renderHook(() => useETLActions(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.triggerReprocessing('user-123');
      });

      expect(mockReprocessMutation.mutate).toHaveBeenCalledWith({
        userId: 'user-123',
        force: false,
      });
    });
  });
});