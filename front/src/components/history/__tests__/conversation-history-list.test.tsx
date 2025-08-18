import * as React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ConversationHistoryList } from '../conversation-history-list';
import { useAuth } from '@/providers/auth-provider';
import { useConversationHistory } from '@/hooks/api-hooks';
import { Conversation } from '@/lib/types';

// Mock dependencies
vi.mock('@/providers/auth-provider');
vi.mock('@/hooks/api-hooks');
vi.mock('@/components/ui/toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

const mockUseAuth = vi.mocked(useAuth);
const mockUseConversationHistory = vi.mocked(useConversationHistory);

const mockUser = {
  id: 'user-123',
  name: 'Test User',
  type: 'personal' as const,
};

const mockConversations: Conversation[] = [
  {
    conversation_id: 'conv-1',
    user_id: 'user-123',
    title: '첫 번째 대화',
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:30:00Z',
    message_count: 5,
    last_message_preview: '안녕하세요, 저의 적성에 대해 알고 싶습니다.',
  },
  {
    conversation_id: 'conv-2',
    user_id: 'user-123',
    created_at: '2024-01-02T14:00:00Z',
    updated_at: '2024-01-02T14:15:00Z',
    message_count: 3,
    last_message_preview: '이전 결과에 대해 더 자세히 설명해주세요.',
  },
];

const mockHistoryResponse = {
  conversations: mockConversations,
  total: 2,
  page: 1,
  limit: 20,
};

function renderWithQueryClient(component: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
}

describe('ConversationHistoryList', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      clearError: vi.fn(),
      validateSession: vi.fn(),
      getToken: vi.fn(),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state correctly', () => {
    mockUseConversationHistory.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(<ConversationHistoryList />);

    // Should show skeleton loading
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders conversation list correctly', () => {
    mockUseConversationHistory.mockReturnValue({
      data: mockHistoryResponse,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(<ConversationHistoryList />);

    // Should show header
    expect(screen.getByText('대화 기록')).toBeInTheDocument();
    expect(screen.getByText('총 2개의 대화')).toBeInTheDocument();

    // Should show conversations
    expect(screen.getByText('첫 번째 대화')).toBeInTheDocument();
    expect(screen.getByText('대화 conv-2')).toBeInTheDocument(); // Fallback title
    expect(screen.getByText('안녕하세요, 저의 적성에 대해 알고 싶습니다.')).toBeInTheDocument();
    expect(screen.getByText('이전 결과에 대해 더 자세히 설명해주세요.')).toBeInTheDocument();

    // Should show message counts
    expect(screen.getByText('5개 메시지')).toBeInTheDocument();
    expect(screen.getByText('3개 메시지')).toBeInTheDocument();
  });

  it('renders empty state correctly', () => {
    mockUseConversationHistory.mockReturnValue({
      data: { conversations: [], total: 0, page: 1, limit: 20 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(<ConversationHistoryList />);

    expect(screen.getByText('아직 대화 기록이 없습니다')).toBeInTheDocument();
    expect(screen.getByText('채팅을 시작하면 대화 기록이 여기에 표시됩니다.')).toBeInTheDocument();
    expect(screen.getByText('채팅 시작하기')).toBeInTheDocument();
  });

  it('renders error state correctly', () => {
    const mockRefetch = vi.fn();
    mockUseConversationHistory.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Network error'),
      refetch: mockRefetch,
    } as any);

    renderWithQueryClient(<ConversationHistoryList />);

    expect(screen.getByText('대화 기록을 불러올 수 없습니다')).toBeInTheDocument();
    expect(screen.getByText('네트워크 연결을 확인하고 다시 시도해주세요.')).toBeInTheDocument();

    const retryButton = screen.getByText('다시 시도');
    fireEvent.click(retryButton);
    expect(mockRefetch).toHaveBeenCalled();
  });

  it('calls onConversationSelect when conversation is clicked', () => {
    const mockOnSelect = vi.fn();
    mockUseConversationHistory.mockReturnValue({
      data: mockHistoryResponse,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationHistoryList onConversationSelect={mockOnSelect} />
    );

    const firstConversation = screen.getByText('첫 번째 대화').closest('[role="button"]');
    expect(firstConversation).toBeInTheDocument();

    fireEvent.click(firstConversation!);
    expect(mockOnSelect).toHaveBeenCalledWith(mockConversations[0]);
  });

  it('handles keyboard navigation correctly', () => {
    const mockOnSelect = vi.fn();
    mockUseConversationHistory.mockReturnValue({
      data: mockHistoryResponse,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationHistoryList onConversationSelect={mockOnSelect} />
    );

    const firstConversation = screen.getByText('첫 번째 대화').closest('[role="button"]');
    expect(firstConversation).toBeInTheDocument();

    // Test Enter key
    fireEvent.keyDown(firstConversation!, { key: 'Enter' });
    expect(mockOnSelect).toHaveBeenCalledWith(mockConversations[0]);

    mockOnSelect.mockClear();

    // Test Space key
    fireEvent.keyDown(firstConversation!, { key: ' ' });
    expect(mockOnSelect).toHaveBeenCalledWith(mockConversations[0]);
  });

  it('renders pagination correctly when there are multiple pages', () => {
    const mockHistoryWithPagination = {
      ...mockHistoryResponse,
      total: 50,
      page: 2,
    };

    mockUseConversationHistory.mockReturnValue({
      data: mockHistoryWithPagination,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(<ConversationHistoryList />);

    expect(screen.getByText('페이지 2 / 3')).toBeInTheDocument();
    expect(screen.getByText('이전')).toBeInTheDocument();
    expect(screen.getByText('다음')).toBeInTheDocument();
  });

  it('does not render pagination when there is only one page', () => {
    mockUseConversationHistory.mockReturnValue({
      data: mockHistoryResponse,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(<ConversationHistoryList />);

    expect(screen.queryByText('페이지')).not.toBeInTheDocument();
    expect(screen.queryByText('이전')).not.toBeInTheDocument();
    expect(screen.queryByText('다음')).not.toBeInTheDocument();
  });

  it('does not fetch data when user is not available', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      clearError: vi.fn(),
      validateSession: vi.fn(),
      getToken: vi.fn(),
    });

    const mockQuery = vi.fn().mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseConversationHistory.mockImplementation(mockQuery);

    renderWithQueryClient(<ConversationHistoryList />);

    // Should be called with empty user ID and enabled: false
    expect(mockQuery).toHaveBeenCalledWith('', 1, 20, { enabled: false });
  });
});