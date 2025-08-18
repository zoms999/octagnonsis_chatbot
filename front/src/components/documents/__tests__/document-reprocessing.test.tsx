import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { DocumentReprocessing } from '../document-reprocessing';
import { AuthUser, ETLJobResponse } from '@/lib/types';

// Mock the auth provider
vi.mock('@/providers/auth-provider', () => ({
  useAuth: vi.fn(),
}));

// Mock the API hooks
vi.mock('@/hooks/api-hooks', () => ({
  useReprocessUserDocuments: vi.fn(),
}));

// Mock the toast hook
vi.mock('@/components/ui/toast', () => ({
  useToast: vi.fn(() => ({
    toast: vi.fn(),
  })),
}));

import { useAuth } from '@/providers/auth-provider';
import { useReprocessUserDocuments } from '@/hooks/api-hooks';
import { useToast } from '@/components/ui/toast';

const mockUser: AuthUser = {
  id: 'user-123',
  name: '홍길동',
  type: 'personal',
};

const mockJobResponse: ETLJobResponse = {
  job_id: 'job-456',
  progress_url: '/api/etl/jobs/job-456/progress',
  estimated_completion_time: '2024-01-15T11:00:00Z',
};

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

describe('DocumentReprocessing', () => {
  const mockToast = vi.fn();
  const mockMutate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useToast as any).mockReturnValue({ toast: mockToast });
    (useReprocessUserDocuments as any).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    });
  });

  it('renders reprocessing component correctly', () => {
    (useAuth as any).mockReturnValue({ user: mockUser });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    expect(screen.getByText('문서 재처리')).toBeInTheDocument();
    expect(screen.getByText('일반 재처리')).toBeInTheDocument();
    expect(screen.getByText('강제 재처리')).toBeInTheDocument();
    
    // Check descriptions
    expect(screen.getByText(/최신 알고리즘으로 적성 분석 결과를 다시 생성/)).toBeInTheDocument();
    expect(screen.getByText(/재처리 중에는 기존 문서가 일시적으로 사용할 수 없을/)).toBeInTheDocument();
  });

  it('shows confirmation dialog for normal reprocessing', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    const normalButton = screen.getByText('일반 재처리');
    fireEvent.click(normalButton);

    await waitFor(() => {
      expect(screen.getByText('재처리 확인')).toBeInTheDocument();
      expect(screen.getByText(/문서 재처리를 시작하시겠습니까/)).toBeInTheDocument();
      expect(screen.getByText('재처리 시작')).toBeInTheDocument();
    });
  });

  it('shows confirmation dialog for force reprocessing', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    const forceButton = screen.getByText('강제 재처리');
    fireEvent.click(forceButton);

    await waitFor(() => {
      expect(screen.getByText('강제 재처리 확인')).toBeInTheDocument();
      expect(screen.getByText(/모든 문서를 강제로 재처리하시겠습니까/)).toBeInTheDocument();
      expect(screen.getByText('강제 재처리')).toBeInTheDocument();
    });
  });

  it('calls reprocess mutation with correct parameters for normal reprocessing', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    // Click normal reprocessing
    const normalButton = screen.getByText('일반 재처리');
    fireEvent.click(normalButton);

    // Confirm in dialog
    await waitFor(() => {
      const confirmButton = screen.getByText('재처리 시작');
      fireEvent.click(confirmButton);
    });

    expect(mockMutate).toHaveBeenCalledWith({
      userId: 'user-123',
      force: false,
    });
  });

  it('calls reprocess mutation with correct parameters for force reprocessing', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    // Click force reprocessing
    const forceButton = screen.getByText('강제 재처리');
    fireEvent.click(forceButton);

    // Confirm in dialog
    await waitFor(() => {
      const confirmButton = screen.getByText('강제 재처리');
      fireEvent.click(confirmButton);
    });

    expect(mockMutate).toHaveBeenCalledWith({
      userId: 'user-123',
      force: true,
    });
  });

  it('shows loading state during reprocessing', () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useReprocessUserDocuments as any).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
    });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    // Buttons should be disabled
    expect(screen.getByText('일반 재처리')).toBeDisabled();
    expect(screen.getByText('강제 재처리')).toBeDisabled();

    // Should show loading message
    expect(screen.getByText('재처리 작업을 시작하고 있습니다...')).toBeInTheDocument();
  });

  it('handles successful reprocessing', () => {
    const mockOnSuccess = vi.fn();
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useReprocessUserDocuments as any).mockImplementation((options: any) => {
      // Simulate successful mutation
      setTimeout(() => options.onSuccess(mockJobResponse), 0);
      return { mutate: mockMutate, isPending: false };
    });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    expect(mockToast).toHaveBeenCalledWith({
      title: '재처리 시작됨',
      description: '문서 재처리가 시작되었습니다. 작업 ID: job-456',
      variant: 'success',
    });
  });

  it('handles reprocessing error', () => {
    const mockError = new Error('Reprocessing failed');
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useReprocessUserDocuments as any).mockImplementation((options: any) => {
      // Simulate error
      setTimeout(() => options.onError(mockError), 0);
      return { mutate: mockMutate, isPending: false };
    });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    expect(mockToast).toHaveBeenCalledWith({
      title: '재처리 실패',
      description: 'Reprocessing failed',
      variant: 'destructive',
    });
  });

  it('handles no user case', () => {
    (useAuth as any).mockReturnValue({ user: null });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    expect(screen.getByText('사용자 정보를 불러올 수 없습니다.')).toBeInTheDocument();
  });

  it('shows error when user ID is missing', async () => {
    (useAuth as any).mockReturnValue({ user: { ...mockUser, id: undefined } });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    const normalButton = screen.getByText('일반 재처리');
    fireEvent.click(normalButton);

    await waitFor(() => {
      const confirmButton = screen.getByText('재처리 시작');
      fireEvent.click(confirmButton);
    });

    expect(mockToast).toHaveBeenCalledWith({
      title: '오류',
      description: '사용자 정보를 찾을 수 없습니다.',
      variant: 'destructive',
    });
  });

  it('cancels reprocessing dialog', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    const normalButton = screen.getByText('일반 재처리');
    fireEvent.click(normalButton);

    await waitFor(() => {
      expect(screen.getByText('재처리 확인')).toBeInTheDocument();
    });

    const cancelButton = screen.getByText('취소');
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByText('재처리 확인')).not.toBeInTheDocument();
    });

    expect(mockMutate).not.toHaveBeenCalled();
  });

  it('displays helpful information about reprocessing types', () => {
    (useAuth as any).mockReturnValue({ user: mockUser });

    render(<DocumentReprocessing />, { wrapper: createWrapper() });

    expect(screen.getByText(/일반 재처리.*기존 처리 상태를 확인하고/)).toBeInTheDocument();
    expect(screen.getByText(/강제 재처리.*기존 상태와 관계없이 모든 문서를/)).toBeInTheDocument();
  });
});