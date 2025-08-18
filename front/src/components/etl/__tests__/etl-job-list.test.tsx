import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ETLJobList } from '../etl-job-list';
import { useETLJobs } from '@/hooks/api-hooks';
import { useAuth } from '@/providers/auth-provider';
import { ETLJob } from '@/lib/types';

// Mock the hooks
vi.mock('@/hooks/api-hooks');
vi.mock('@/providers/auth-provider');

const mockUseETLJobs = useETLJobs as any;
const mockUseAuth = useAuth as any;

// Mock date-fns
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '2 minutes ago'),
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

describe('ETLJobList', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: { id: 'user-123', name: 'Test User', type: 'personal' },
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    mockUseETLJobs.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ETLJobList />, { wrapper: createWrapper() });

    expect(screen.getByText('Loading ETL jobs...')).toBeInTheDocument();
  });

  it('renders error state with retry button', () => {
    const mockRefetch = vi.fn();
    mockUseETLJobs.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { message: 'Failed to load jobs' },
      refetch: mockRefetch,
    } as any);

    render(<ETLJobList />, { wrapper: createWrapper() });

    expect(screen.getByText('Failed to load ETL jobs')).toBeInTheDocument();
    expect(screen.getByText('Failed to load jobs')).toBeInTheDocument();
    
    const retryButton = screen.getByText('Retry');
    fireEvent.click(retryButton);
    expect(mockRefetch).toHaveBeenCalled();
  });

  it('renders empty state when no jobs exist', () => {
    mockUseETLJobs.mockReturnValue({
      data: { jobs: [], total: 0, page: 1, limit: 10 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ETLJobList />, { wrapper: createWrapper() });

    expect(screen.getByText('No ETL jobs found')).toBeInTheDocument();
    expect(screen.getByText('No processing jobs have been created for your account yet.')).toBeInTheDocument();
  });

  it('renders job list with correct data', () => {
    mockUseETLJobs.mockReturnValue({
      data: { jobs: mockJobs, total: 3, page: 1, limit: 10 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ETLJobList />, { wrapper: createWrapper() });

    // Check header
    expect(screen.getByText('ETL Jobs (3)')).toBeInTheDocument();

    // Check job cards
    expect(screen.getByText('job-123...')).toBeInTheDocument();
    expect(screen.getByText('Processing documents')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();

    expect(screen.getByText('job-456...')).toBeInTheDocument();
    expect(screen.getByText('Completed successfully')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();

    expect(screen.getByText('job-789...')).toBeInTheDocument();
    expect(screen.getByText('Document processing failed')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('Invalid document format')).toBeInTheDocument();
  });

  it('handles job selection', () => {
    const mockOnJobSelect = vi.fn();
    mockUseETLJobs.mockReturnValue({
      data: { jobs: mockJobs, total: 3, page: 1, limit: 10 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ETLJobList onJobSelect={mockOnJobSelect} />, { wrapper: createWrapper() });

    const firstJobCard = screen.getByText('job-123...').closest('div');
    fireEvent.click(firstJobCard!);

    expect(mockOnJobSelect).toHaveBeenCalledWith(mockJobs[0]);
  });

  it('shows selected job with visual indicator', () => {
    mockUseETLJobs.mockReturnValue({
      data: { jobs: mockJobs, total: 3, page: 1, limit: 10 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<ETLJobList selectedJobId="job-123" />, { wrapper: createWrapper() });

    // Find the job card container (not just the text element)
    const jobCards = screen.getAllByText(/job-123/).map(el => {
      // Find the parent card container
      let parent = el.parentElement;
      while (parent && !parent.className.includes('p-4 border rounded-lg')) {
        parent = parent.parentElement;
      }
      return parent;
    }).filter(Boolean);

    const selectedCard = jobCards.find(card => 
      card?.className.includes('border-blue-500') && 
      card?.className.includes('bg-blue-50')
    );
    
    expect(selectedCard).toBeTruthy();
  });

  it('calls refetch when refresh button is clicked', () => {
    const mockRefetch = vi.fn();
    mockUseETLJobs.mockReturnValue({
      data: { jobs: mockJobs, total: 3, page: 1, limit: 10 },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    } as any);

    render(<ETLJobList />, { wrapper: createWrapper() });

    const refreshButton = screen.getByText('🔄 Refresh');
    fireEvent.click(refreshButton);

    expect(mockRefetch).toHaveBeenCalled();
  });
});