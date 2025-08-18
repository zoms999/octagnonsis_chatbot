import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ETLJobDetail } from '../etl-job-detail';
import { ReprocessingTrigger } from '../reprocessing-trigger';
import { useETLActions } from '@/hooks/use-etl-actions';
import { useAuth } from '@/providers/auth-provider';
import { ETLJob } from '@/lib/types';

// Mock hooks
vi.mock('@/hooks/use-etl-actions');
vi.mock('@/providers/auth-provider');
vi.mock('@/hooks/api-hooks', () => ({
  useETLJobStatus: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
  })),
}));

const mockETLActions = {
  retryJob: vi.fn(),
  cancelJob: vi.fn(),
  triggerReprocessing: vi.fn(),
  isRetrying: vi.fn(),
  isCancelling: vi.fn(),
  isReprocessing: vi.fn(),
  canRetryJob: vi.fn(),
  canCancelJob: vi.fn(),
  isAnyActionLoading: false,
};

const mockAuth = {
  user: {
    id: 'user-123',
    name: 'Test User',
    type: 'personal' as const,
  },
  isAuthenticated: true,
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
};

const mockFailedJob: ETLJob = {
  job_id: 'job-123',
  status: 'failed',
  progress: 0,
  current_step: 'Failed at document processing',
  error_message: 'Connection timeout',
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T10:30:00Z',
};

const mockRunningJob: ETLJob = {
  job_id: 'job-456',
  status: 'running',
  progress: 50,
  current_step: 'Processing documents',
  created_at: '2024-01-01T11:00:00Z',
  updated_at: '2024-01-01T11:15:00Z',
};

function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe('ETL Job Actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useETLActions as any).mockReturnValue(mockETLActions);
    (useAuth as any).mockReturnValue(mockAuth);
  });

  describe('ETLJobDetail Actions', () => {
    it('should show retry button for failed jobs', () => {
      mockETLActions.canRetryJob.mockReturnValue(true);
      mockETLActions.canCancelJob.mockReturnValue(false);
      mockETLActions.isRetrying.mockReturnValue(false);

      render(
        <TestWrapper>
          <ETLJobDetail job={mockFailedJob} />
        </TestWrapper>
      );

      expect(screen.getByText('🔄 Retry Job')).toBeInTheDocument();
      expect(screen.queryByText('⏹️ Cancel Job')).not.toBeInTheDocument();
    });

    it('should show cancel button for running jobs', () => {
      mockETLActions.canRetryJob.mockReturnValue(false);
      mockETLActions.canCancelJob.mockReturnValue(true);
      mockETLActions.isCancelling.mockReturnValue(false);

      render(
        <TestWrapper>
          <ETLJobDetail job={mockRunningJob} />
        </TestWrapper>
      );

      expect(screen.getByText('⏹️ Cancel Job')).toBeInTheDocument();
      expect(screen.queryByText('🔄 Retry Job')).not.toBeInTheDocument();
    });

    it('should open confirmation dialog when retry is clicked', async () => {
      mockETLActions.canRetryJob.mockReturnValue(true);
      mockETLActions.isRetrying.mockReturnValue(false);

      render(
        <TestWrapper>
          <ETLJobDetail job={mockFailedJob} />
        </TestWrapper>
      );

      fireEvent.click(screen.getByText('🔄 Retry Job'));

      await waitFor(() => {
        expect(screen.getByText('Retry ETL Job')).toBeInTheDocument();
        expect(screen.getByText(/Are you sure you want to retry job/)).toBeInTheDocument();
      });
    });

    it('should open confirmation dialog when cancel is clicked', async () => {
      mockETLActions.canCancelJob.mockReturnValue(true);
      mockETLActions.isCancelling.mockReturnValue(false);

      render(
        <TestWrapper>
          <ETLJobDetail job={mockRunningJob} />
        </TestWrapper>
      );

      fireEvent.click(screen.getByText('⏹️ Cancel Job'));

      await waitFor(() => {
        expect(screen.getByText('Cancel ETL Job')).toBeInTheDocument();
        expect(screen.getByText(/Are you sure you want to cancel job/)).toBeInTheDocument();
      });
    });

    it('should call retryJob when confirmed', async () => {
      mockETLActions.canRetryJob.mockReturnValue(true);
      mockETLActions.isRetrying.mockReturnValue(false);

      render(
        <TestWrapper>
          <ETLJobDetail job={mockFailedJob} />
        </TestWrapper>
      );

      fireEvent.click(screen.getByText('🔄 Retry Job'));

      await waitFor(() => {
        expect(screen.getByText('Retry Job')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Retry Job'));

      expect(mockETLActions.retryJob).toHaveBeenCalledWith('job-123');
    });

    it('should call cancelJob when confirmed', async () => {
      mockETLActions.canCancelJob.mockReturnValue(true);
      mockETLActions.isCancelling.mockReturnValue(false);

      render(
        <TestWrapper>
          <ETLJobDetail job={mockRunningJob} />
        </TestWrapper>
      );

      fireEvent.click(screen.getByText('⏹️ Cancel Job'));

      await waitFor(() => {
        expect(screen.getByText('Cancel Job')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Cancel Job'));

      expect(mockETLActions.cancelJob).toHaveBeenCalledWith('job-456');
    });

    it('should show loading state when retrying', () => {
      mockETLActions.canRetryJob.mockReturnValue(true);
      mockETLActions.isRetrying.mockReturnValue(true);

      render(
        <TestWrapper>
          <ETLJobDetail job={mockFailedJob} />
        </TestWrapper>
      );

      expect(screen.getByText('Retrying...')).toBeInTheDocument();
    });

    it('should show loading state when cancelling', () => {
      mockETLActions.canCancelJob.mockReturnValue(true);
      mockETLActions.isCancelling.mockReturnValue(true);

      render(
        <TestWrapper>
          <ETLJobDetail job={mockRunningJob} />
        </TestWrapper>
      );

      expect(screen.getByText('Cancelling...')).toBeInTheDocument();
    });
  });

  describe('ReprocessingTrigger', () => {
    it('should render reprocessing buttons', () => {
      mockETLActions.isReprocessing.mockReturnValue(false);

      render(
        <TestWrapper>
          <ReprocessingTrigger />
        </TestWrapper>
      );

      expect(screen.getByText('🔄 Reprocess Documents')).toBeInTheDocument();
      expect(screen.getByText('Force Reprocess')).toBeInTheDocument();
    });

    it('should open confirmation dialog for normal reprocess', async () => {
      mockETLActions.isReprocessing.mockReturnValue(false);

      render(
        <TestWrapper>
          <ReprocessingTrigger />
        </TestWrapper>
      );

      fireEvent.click(screen.getByText('🔄 Reprocess Documents'));

      await waitFor(() => {
        expect(screen.getByText('Reprocess Documents')).toBeInTheDocument();
        expect(screen.getByText(/This will reprocess your documents/)).toBeInTheDocument();
      });
    });

    it('should open confirmation dialog for force reprocess', async () => {
      mockETLActions.isReprocessing.mockReturnValue(false);

      render(
        <TestWrapper>
          <ReprocessingTrigger />
        </TestWrapper>
      );

      fireEvent.click(screen.getByText('Force Reprocess'));

      await waitFor(() => {
        expect(screen.getByText('Force Reprocess All Documents')).toBeInTheDocument();
        expect(screen.getByText(/This will force reprocessing of ALL/)).toBeInTheDocument();
      });
    });

    it('should call triggerReprocessing with correct parameters', async () => {
      mockETLActions.isReprocessing.mockReturnValue(false);

      render(
        <TestWrapper>
          <ReprocessingTrigger />
        </TestWrapper>
      );

      // Test normal reprocess
      fireEvent.click(screen.getByText('🔄 Reprocess Documents'));

      await waitFor(() => {
        expect(screen.getByText('Start Reprocessing')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Start Reprocessing'));

      expect(mockETLActions.triggerReprocessing).toHaveBeenCalledWith('user-123', false);
    });

    it('should show loading state when reprocessing', () => {
      mockETLActions.isReprocessing.mockReturnValue(true);

      render(
        <TestWrapper>
          <ReprocessingTrigger />
        </TestWrapper>
      );

      expect(screen.getByText('Processing...')).toBeInTheDocument();
    });

    it('should not render when user is not authenticated', () => {
      (useAuth as any).mockReturnValue({
        ...mockAuth,
        user: null,
        isAuthenticated: false,
      });

      const { container } = render(
        <TestWrapper>
          <ReprocessingTrigger />
        </TestWrapper>
      );

      expect(container.firstChild).toBeNull();
    });
  });
});