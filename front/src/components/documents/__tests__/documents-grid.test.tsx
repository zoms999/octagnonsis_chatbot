import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { DocumentsGrid } from '../documents-grid';
import { AuthUser, UserDocumentsResponse } from '@/lib/types';

// Mock the auth provider
vi.mock('@/providers/auth-provider', () => ({
  useAuth: vi.fn(),
}));

// Mock the API hooks
vi.mock('@/hooks/api-hooks', () => ({
  useUserDocuments: vi.fn(),
}));

import { useAuth } from '@/providers/auth-provider';
import { useUserDocuments } from '@/hooks/api-hooks';

const mockUser: AuthUser = {
  id: 'user-123',
  name: '홍길동',
  type: 'personal',
};

const mockDocumentsResponse: UserDocumentsResponse = {
  documents: [
    {
      id: 'doc-1',
      doc_type: 'primary_tendency',
      title: '주요 성향 분석 결과',
      preview: {
        primary_tendency: '분석적이고 논리적인 성향',
      },
      created_at: '2024-01-15T10:30:00Z',
      updated_at: '2024-01-15T10:30:00Z',
    },
    {
      id: 'doc-2',
      doc_type: 'top_skills',
      title: '상위 기술 분석',
      preview: {
        top_skills: ['문제해결', '분석적 사고', '의사소통', '리더십', '창의성'],
      },
      created_at: '2024-01-14T09:20:00Z',
      updated_at: '2024-01-14T09:20:00Z',
    },
    {
      id: 'doc-3',
      doc_type: 'top_jobs',
      title: '추천 직업 목록',
      preview: {
        top_jobs: ['소프트웨어 개발자', '데이터 분석가', '프로젝트 매니저'],
      },
      created_at: '2024-01-13T14:15:00Z',
      updated_at: '2024-01-13T14:15:00Z',
    },
  ],
  total: 3,
  page: 1,
  limit: 12,
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

describe('DocumentsGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders documents grid correctly', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserDocuments as any).mockReturnValue({
      data: mockDocumentsResponse,
      isLoading: false,
      error: null,
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    // Check if documents are displayed
    expect(screen.getByText('주요 성향 분석 결과')).toBeInTheDocument();
    expect(screen.getByText('상위 기술 분석')).toBeInTheDocument();
    expect(screen.getByText('추천 직업 목록')).toBeInTheDocument();

    // Check document type badges
    expect(screen.getByText('주요 성향')).toBeInTheDocument();
    expect(screen.getByText('상위 기술')).toBeInTheDocument();
    expect(screen.getByText('추천 직업')).toBeInTheDocument();
  });

  it('displays search and filter controls', () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserDocuments as any).mockReturnValue({
      data: mockDocumentsResponse,
      isLoading: false,
      error: null,
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    // Check search input
    expect(screen.getByPlaceholderText('문서 제목이나 유형으로 검색...')).toBeInTheDocument();

    // Check filter dropdown
    expect(screen.getByDisplayValue('모든 유형')).toBeInTheDocument();
  });

  it('filters documents by search term', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserDocuments as any).mockReturnValue({
      data: mockDocumentsResponse,
      isLoading: false,
      error: null,
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    const searchInput = screen.getByPlaceholderText('문서 제목이나 유형으로 검색...');
    
    // Search for "주요"
    fireEvent.change(searchInput, { target: { value: '주요' } });

    await waitFor(() => {
      expect(screen.getByText('주요 성향 분석 결과')).toBeInTheDocument();
      expect(screen.queryByText('상위 기술 분석')).not.toBeInTheDocument();
      expect(screen.queryByText('추천 직업 목록')).not.toBeInTheDocument();
    });
  });

  it('filters documents by type', async () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserDocuments as any).mockReturnValue({
      data: mockDocumentsResponse,
      isLoading: false,
      error: null,
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    const filterSelect = screen.getByDisplayValue('모든 유형');
    
    // Filter by "주요 성향"
    fireEvent.change(filterSelect, { target: { value: 'primary_tendency' } });

    // The useUserDocuments hook should be called with the filter
    expect(useUserDocuments).toHaveBeenCalledWith('user-123', 1, 12, 'primary_tendency');
  });

  it('displays document previews correctly', () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserDocuments as any).mockReturnValue({
      data: mockDocumentsResponse,
      isLoading: false,
      error: null,
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    // Check primary tendency preview
    expect(screen.getByText('분석적이고 논리적인 성향')).toBeInTheDocument();

    // Check skills preview (should show badges)
    expect(screen.getByText('문제해결')).toBeInTheDocument();
    expect(screen.getByText('분석적 사고')).toBeInTheDocument();
    expect(screen.getByText('+2')).toBeInTheDocument(); // Shows +2 for remaining skills

    // Check jobs preview
    expect(screen.getByText('소프트웨어 개발자')).toBeInTheDocument();
    expect(screen.getByText('데이터 분석가')).toBeInTheDocument();
    expect(screen.getByText('+1')).toBeInTheDocument(); // Shows +1 for remaining job
  });

  it('displays loading state', () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserDocuments as any).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    // Should show skeleton cards
    expect(document.querySelectorAll('.animate-pulse')).toHaveLength(6);
  });

  it('displays error state', () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserDocuments as any).mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('API Error'),
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    expect(screen.getByText('문서를 불러오는 중 오류가 발생했습니다.')).toBeInTheDocument();
    expect(screen.getByText('잠시 후 다시 시도해주세요.')).toBeInTheDocument();
  });

  it('displays empty state when no documents', () => {
    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserDocuments as any).mockReturnValue({
      data: { documents: [], total: 0, page: 1, limit: 12 },
      isLoading: false,
      error: null,
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    expect(screen.getByText('문서가 없습니다')).toBeInTheDocument();
    expect(screen.getByText('아직 처리된 문서가 없습니다. ETL 처리를 통해 문서를 생성해보세요.')).toBeInTheDocument();
  });

  it('displays no user state', () => {
    (useAuth as any).mockReturnValue({ user: null });
    (useUserDocuments as any).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    expect(screen.getByText('사용자 정보를 불러올 수 없습니다.')).toBeInTheDocument();
  });

  it('handles pagination correctly', () => {
    const mockResponseWithPagination: UserDocumentsResponse = {
      ...mockDocumentsResponse,
      total: 25, // More than 12 items per page
    };

    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserDocuments as any).mockReturnValue({
      data: mockResponseWithPagination,
      isLoading: false,
      error: null,
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    // Should show pagination controls
    expect(screen.getByText('이전')).toBeInTheDocument();
    expect(screen.getByText('다음')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('navigates pages correctly', async () => {
    const mockResponseWithPagination: UserDocumentsResponse = {
      ...mockDocumentsResponse,
      total: 25,
    };

    (useAuth as any).mockReturnValue({ user: mockUser });
    (useUserDocuments as any).mockReturnValue({
      data: mockResponseWithPagination,
      isLoading: false,
      error: null,
    });

    render(<DocumentsGrid />, { wrapper: createWrapper() });

    const nextButton = screen.getByText('다음');
    fireEvent.click(nextButton);

    // Should call useUserDocuments with page 2
    await waitFor(() => {
      expect(useUserDocuments).toHaveBeenCalledWith('user-123', 2, 12, undefined);
    });
  });
});