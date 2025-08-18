import * as React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ConversationDetailModal } from '../conversation-detail-modal';
import { useConversationDetail } from '@/hooks/api-hooks';
import { Conversation, ConversationDetail, ChatMessage } from '@/lib/types';

// Mock dependencies
vi.mock('@/hooks/api-hooks');
vi.mock('@/components/ui/toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

const mockUseConversationDetail = vi.mocked(useConversationDetail);

const mockConversation: Conversation = {
  conversation_id: 'conv-123',
  user_id: 'user-123',
  title: '테스트 대화',
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T10:30:00Z',
  message_count: 3,
  last_message_preview: '마지막 메시지 미리보기',
};

const mockMessages: ChatMessage[] = [
  {
    id: 'msg-1',
    type: 'user',
    content: '안녕하세요, 저의 적성에 대해 알고 싶습니다.',
    timestamp: new Date('2024-01-01T10:00:00Z'),
    conversation_id: 'conv-123',
  },
  {
    id: 'msg-2',
    type: 'assistant',
    content: '안녕하세요! 적성 분석에 대해 도움을 드리겠습니다.',
    timestamp: new Date('2024-01-01T10:01:00Z'),
    confidence_score: 0.85,
    processing_time: 1.2,
    retrieved_documents: [
      {
        id: 'doc-1',
        type: 'primary_tendency',
        title: '주요 성향 분석',
        preview: '분석 결과 미리보기',
        relevance_score: 0.9,
      },
    ],
    conversation_id: 'conv-123',
  },
  {
    id: 'msg-3',
    type: 'user',
    content: '더 자세한 설명을 부탁드립니다.',
    timestamp: new Date('2024-01-01T10:02:00Z'),
    conversation_id: 'conv-123',
  },
];

const mockConversationDetail: ConversationDetail = {
  conversation_id: 'conv-123',
  messages: mockMessages,
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T10:30:00Z',
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

describe('ConversationDetailModal', () => {
  const mockOnClose = vi.fn();
  const mockOnNavigateToConversation = vi.fn();

  beforeEach(() => {
    // Mock window.location.href
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when conversation is null', () => {
    mockUseConversationDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={null}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    expect(screen.queryByText('테스트 대화')).not.toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    mockUseConversationDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={mockConversation}
        isOpen={false}
        onClose={mockOnClose}
      />
    );

    expect(screen.queryByText('테스트 대화')).not.toBeInTheDocument();
  });

  it('renders loading state correctly', () => {
    mockUseConversationDetail.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={mockConversation}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    expect(screen.getAllByText('테스트 대화')).toHaveLength(2); // Modal title and content title
    // Should show skeleton loading
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders conversation detail correctly', () => {
    mockUseConversationDetail.mockReturnValue({
      data: mockConversationDetail,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={mockConversation}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    // Should show conversation title
    expect(screen.getAllByText('테스트 대화')).toHaveLength(2); // Modal title and content title

    // Should show conversation metadata
    expect(screen.getByText('3개 메시지')).toBeInTheDocument();

    // Should show messages
    expect(screen.getByText('안녕하세요, 저의 적성에 대해 알고 싶습니다.')).toBeInTheDocument();
    expect(screen.getByText('안녕하세요! 적성 분석에 대해 도움을 드리겠습니다.')).toBeInTheDocument();
    expect(screen.getByText('더 자세한 설명을 부탁드립니다.')).toBeInTheDocument();

    // Should show assistant message metadata
    expect(screen.getByText('85%')).toBeInTheDocument(); // confidence score
    expect(screen.getByText('처리 시간: 1.20초')).toBeInTheDocument();
    expect(screen.getByText('참조 문서: 1개')).toBeInTheDocument();
  });

  it('renders error state correctly', () => {
    const mockRefetch = vi.fn();
    mockUseConversationDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Network error'),
      refetch: mockRefetch,
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={mockConversation}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('대화 내용을 불러올 수 없습니다')).toBeInTheDocument();
    expect(screen.getByText('네트워크 연결을 확인하고 다시 시도해주세요.')).toBeInTheDocument();

    const retryButton = screen.getByText('다시 시도');
    fireEvent.click(retryButton);
    expect(mockRefetch).toHaveBeenCalled();
  });

  it('renders empty messages state correctly', () => {
    const emptyConversationDetail = {
      ...mockConversationDetail,
      messages: [],
    };

    mockUseConversationDetail.mockReturnValue({
      data: emptyConversationDetail,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={mockConversation}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText('메시지가 없습니다')).toBeInTheDocument();
    expect(screen.getByText('이 대화에는 아직 메시지가 없습니다.')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    mockUseConversationDetail.mockReturnValue({
      data: mockConversationDetail,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={mockConversation}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const closeButton = screen.getByText('닫기');
    fireEvent.click(closeButton);
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('calls onClose when Escape key is pressed', () => {
    mockUseConversationDetail.mockReturnValue({
      data: mockConversationDetail,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={mockConversation}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    // Find the modal content div and trigger keydown
    const modalContent = document.querySelector('[tabindex="-1"]');
    expect(modalContent).toBeInTheDocument();

    fireEvent.keyDown(modalContent!, { key: 'Escape' });
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('navigates to chat when "채팅으로 이동" button is clicked', () => {
    mockUseConversationDetail.mockReturnValue({
      data: mockConversationDetail,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={mockConversation}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    const navigateButton = screen.getByText('채팅으로 이동');
    fireEvent.click(navigateButton);

    expect(window.location.href).toBe('/chat?conversation=conv-123');
  });

  it('renders conversation with fallback title when title is not provided', () => {
    const conversationWithoutTitle = {
      ...mockConversation,
      title: undefined,
    };

    mockUseConversationDetail.mockReturnValue({
      data: mockConversationDetail,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={conversationWithoutTitle}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    expect(screen.getAllByText('대화 conv-123')).toHaveLength(2); // Modal title and content title
  });

  it('does not fetch data when modal is closed', () => {
    const mockQuery = vi.fn().mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseConversationDetail.mockImplementation(mockQuery);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={mockConversation}
        isOpen={false}
        onClose={mockOnClose}
      />
    );

    // Should be called with enabled: false when modal is closed
    expect(mockQuery).toHaveBeenCalledWith('conv-123', { enabled: false });
  });

  it('renders message bubbles with correct styling', () => {
    mockUseConversationDetail.mockReturnValue({
      data: mockConversationDetail,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithQueryClient(
      <ConversationDetailModal
        conversation={mockConversation}
        isOpen={true}
        onClose={mockOnClose}
      />
    );

    // Check that user and assistant messages have different styling
    const userMessageBubble = screen.getByText('안녕하세요, 저의 적성에 대해 알고 싶습니다.').parentElement;
    const assistantMessageBubble = screen.getByText('안녕하세요! 적성 분석에 대해 도움을 드리겠습니다.').parentElement;

    expect(userMessageBubble).toHaveClass('bg-primary');
    expect(assistantMessageBubble).toHaveClass('bg-muted');
  });
});