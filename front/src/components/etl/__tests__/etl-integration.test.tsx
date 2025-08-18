import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ETLJobList } from '../etl-job-list';
import { ETLJobDetail } from '../etl-job-detail';
import { ETLJobStats } from '../etl-job-stats';
import { useETLJobs, useETLJobStatus, useRetryETLJob, useCancelETLJob } from '@/hooks/api-hooks';
import { useAuth } from '@/providers/auth-provider';
import { ETLJob } from '@/lib/types';

// Mock the hooks
vi.mock('@/hooks/api-hooks');
vi.mock('@/providers/auth-provider');

const mockUseETLJobs = useETLJobs as any;
const mockUseETLJobStatus = useETLJobStatus as any;
const mockUseRetryETLJob = useRetryETLJob as any;
const mockUseCancelETLJob = useCancelETLJob as any;
const mockUseAuth = useAuth as any;

// Mock date-fns
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '2 minutes ago'),
  format: vi.fn(() => 'Jan 1, 2024, 12:00 PM'),
}));

const mockJobs: ETLJob[] = [
  {
    job_id: 'job-123',
    status: 'running',
    progress: 65,
    current_step: 'Processing documents',
    estimated_completion_time: '2024-01-01T12:30:00Z',
    created_at: '2024-01-01T12:00:00Z',
    updated_at: '2024-01-01T12:15:00Z',
  },
  {
    job_id: 'job-456',
    status: 'completed',
    progress: 100,
    current_step: 'Completed successfully',
    created_at: '2024-01-01T11:00:00Z',
    updated_at: '2024-01-01T11:30:00Z',
  },
  {
    job_id: 'job-789',
    status: 'failed',
    progress: 30,
    current_step: 'Document processing failed',
    error_message: 'Invalid document format',
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:15:00Z',
  },
];

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

// Integration component that combines list, detail, and stats
function ETLMonitoringDashboard() {
  const [selectedJob, setSelectedJob] = React.useState<ETLJob | null>(null);
  const { user } = useAuth();
  
  const { data: jobsResponse } = useETLJobs(user?.id || '', 1, 10);
  const jobs = jobsResponse?.jobs || [];

  const retryMutation = useRetryETLJob();
  const cancelMutation = useCancelETLJob();

  const handleRetry = (jobId: string) => {
    retryMutation.mutate(jobId);
  };

  const handleCancel = (jobId: string) => {
    cancelMutation.mutate(jobId);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Stats */}
      <div className="lg:col-span-3">
        <ETLJobStats jobs={jobs} />
      </div>
      
      {/* Job List */}
      <div className="lg:col-span-2">
        <ETLJobList
          onJobSelect={setSelectedJob}
          selectedJobId={selectedJob?.job_id}
        />
      </div>
      
      {/* Job Detail */}
      <div>
        {selectedJob ? (
          <ETLJobDetail
            job={selectedJob}
            onRetry={handleRetry}
            onCancel={handleCancel}
            isRetrying={retryMutation.isPending}
            isCancelling={cancelMutation.isPending}
          />
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
            <p className="text-gray-600">Select a job to view details</p>
          </div>
        )}
      </div>
    </div>
  );
}

describe('ETL Integration', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: { id: 'user-123', name: 'Test User', type: 'personal' },
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
    });

    mockUseETLJobs.mockReturnValue({
      data: { jobs: mockJobs, total: 3, page: 1, limit: 10 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    mockUseETLJobStatus.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    } as any);

    mockUseRetryETLJob.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    mockUseCancelETLJob.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders complete ETL monitoring dashboard', () => {
    render(<ETLMonitoringDashboard />, { wrapper: createWrapper() });

    // Check stats are displayed
    expect(screen.getByText('Total Jobs')).toBeInTheDocument();
    expect(screen.getByText('Active Jobs')).toBeInTheDocument();
    expect(screen.getAllByText('Completed').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Failed').length).toBeGreaterThan(0);

    // Check job list is displayed
    expect(screen.getByText('ETL Jobs (3)')).toBeInTheDocument();
    expect(screen.getByText('job-123...')).toBeInTheDocument();

    // Check initial state shows selection prompt
    expect(screen.getByText('Select a job to view details')).toBeInTheDocument();
  });

  it('shows job details when job is selected', async () => {
    render(<ETLMonitoringDashboard />, { wrapper: createWrapper() });

    // Click on a job
    const jobCard = screen.getByText('job-123...').closest('div');
    fireEvent.click(jobCard!);

    await waitFor(() => {
      expect(screen.getByText('Job Details')).toBeInTheDocument();
      expect(screen.getByText('job-123')).toBeInTheDocument();
      // Check for the specific context where "Processing documents" appears in job detail
      expect(screen.getAllByText('Processing documents').length).toBeGreaterThan(0);
    });
  });

  it('enables real-time status polling for running jobs', () => {
    render(<ETLMonitoringDashboard />, { wrapper: createWrapper() });

    // Select running job
    const runningJobCard = screen.getByText('job-123...').closest('div');
    fireEvent.click(runningJobCard!);

    // Verify that useETLJobStatus was called with the correct job ID
    expect(mockUseETLJobStatus).toHaveBeenCalledWith('job-123', {
      enabled: true, // Should be enabled for running jobs
    });
  });

  it('handles job retry action', async () => {
    const mockRetryMutate = vi.fn();
    mockUseRetryETLJob.mockReturnValue({
      mutate: mockRetryMutate,
      isPending: false,
    } as any);

    render(<ETLMonitoringDashboard />, { wrapper: createWrapper() });

    // Select failed job
    const failedJobCard = screen.getByText('job-789...').closest('div');
    fireEvent.click(failedJobCard!);

    await waitFor(() => {
      const retryButton = screen.getByText('🔄 Retry Job');
      fireEvent.click(retryButton);
      expect(mockRetryMutate).toHaveBeenCalledWith('job-789');
    });
  });

  it('handles job cancel action', async () => {
    const mockCancelMutate = vi.fn();
    mockUseCancelETLJob.mockReturnValue({
      mutate: mockCancelMutate,
      isPending: false,
    } as any);

    render(<ETLMonitoringDashboard />, { wrapper: createWrapper() });

    // Select running job
    const runningJobCard = screen.getByText('job-123...').closest('div');
    fireEvent.click(runningJobCard!);

    await waitFor(() => {
      const cancelButton = screen.getByText('⏹️ Cancel Job');
      fireEvent.click(cancelButton);
      expect(mockCancelMutate).toHaveBeenCalledWith('job-123');
    });
  });
});