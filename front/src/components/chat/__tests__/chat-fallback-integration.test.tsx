import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChatContainer } from '../chat-container';
import { useWebSocketChat } from '@/hooks/websocket-hooks';

// Mock the WebSocket hook
vi.mock('@/hooks/websocket-hooks', () => ({
  useWebSocketChat: vi.fn(),
}));

// Mock the auth provider
vi.mock('@/providers/auth-provider', () => ({
  useAuth: () => ({
    user: { id: 'user-123', name: 'Test User' },
    getToken: () => Promise.resolve('mock-token'),
  }),
}));

// Mock the document panel hook
vi.mock('@/hooks/use-document-panel', () => ({
  useDocumentPanel: () => ({
    documents: [],
    hasDocuments: false,
    isCollapsed: true,
    isMobile: false,
    toggleCollapsed: vi.fn(),
    updateDocuments: vi.fn(),
  }),
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

describe('Chat Fallback Integration', () => {
  const mockWebSocketChat = {
    sendQuestion: vi.fn(),
    isProcessing: false,
    lastResponse: null,
    lastError: null,
    connectionState: { status: 'connected', reconnectAttempts: 0 },
    isConnected: true,
    rateLimitStatus: {
      canSendMessage: true,
      remainingMessages: 10,
      timeUntilNextMessage: 0,
    },
    usedFallback: false,
    fallbackStatus: {
      isWebSocketAvailable: true,
      fallbackActive: false,
      shouldUseFallback: false,
    },
    forceFallback: vi.fn(),
    disableFallback: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useWebSocketChat as any).mockReturnValue(mockWebSocketChat);
  });

  it('shows normal chat interface when WebSocket is connected', () => {
    render(
      <ChatContainer userHasDocuments={true} />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByText(/연결 끊김/)).not.toBeInTheDocument();
    expect(screen.queryByText(/HTTP 모드/)).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText(/적성 분석에 대해 궁금한 것을 물어보세요/)).toBeInTheDocument();
  });

  it('shows connection status when WebSocket is disconnected', () => {
    (useWebSocketChat as any).mockReturnValue({
      ...mockWebSocketChat,
      isConnected: false,
      connectionState: { status: 'disconnected', reconnectAttempts: 1 },
    });

    render(
      <ChatContainer userHasDocuments={true} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/연결 끊김/)).toBeInTheDocument();
  });

  it('shows HTTP fallback indicator when using fallback', () => {
    (useWebSocketChat as any).mockReturnValue({
      ...mockWebSocketChat,
      isConnected: false,
      usedFallback: true,
      connectionState: { status: 'disconnected', reconnectAttempts: 1 },
    });

    render(
      <ChatContainer userHasDocuments={true} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getAllByText(/HTTP 모드/)).toHaveLength(2);
    expect(screen.getByText(/현재 HTTP 모드로 동작 중입니다/)).toBeInTheDocument();
  });

  it('allows sending messages when fallback is active', async () => {
    (useWebSocketChat as any).mockReturnValue({
      ...mockWebSocketChat,
      isConnected: false,
      usedFallback: true,
    });

    render(
      <ChatContainer userHasDocuments={true} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByPlaceholderText(/적성 분석에 대해 궁금한 것을 물어보세요/);
    const sendButton = screen.getByRole('button', { name: /전송/ });

    fireEvent.change(input, { target: { value: 'Test question' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(mockWebSocketChat.sendQuestion).toHaveBeenCalledWith('Test question', undefined);
    });
  });

  it('shows waiting message when WebSocket is disconnected and no fallback', () => {
    (useWebSocketChat as any).mockReturnValue({
      ...mockWebSocketChat,
      isConnected: false,
      usedFallback: false,
    });

    render(
      <ChatContainer userHasDocuments={true} />,
      { wrapper: createWrapper() }
    );

    const input = screen.getByPlaceholderText(/연결을 기다리는 중/);
    expect(input).toBeInTheDocument();
    // Input should still be enabled as fallback is always available
    expect(input).not.toBeDisabled();
  });

  it('shows processing status during message processing', () => {
    (useWebSocketChat as any).mockReturnValue({
      ...mockWebSocketChat,
      isProcessing: true,
    });

    render(
      <ChatContainer userHasDocuments={true} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/질문을 분석하고 관련 문서를 검색하고 있습니다/)).toBeInTheDocument();
  });

  it('handles response messages correctly', () => {
    const mockResponse = {
      conversation_id: 'conv-123',
      response: 'This is a test response',
      retrieved_documents: [],
      confidence_score: 0.8,
      processing_time: 1500,
      timestamp: new Date().toISOString(),
    };

    (useWebSocketChat as any).mockReturnValue({
      ...mockWebSocketChat,
      lastResponse: mockResponse,
    });

    render(
      <ChatContainer userHasDocuments={true} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('This is a test response')).toBeInTheDocument();
  });

  it('handles error messages correctly', () => {
    (useWebSocketChat as any).mockReturnValue({
      ...mockWebSocketChat,
      lastError: 'Connection failed',
    });

    render(
      <ChatContainer userHasDocuments={true} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/죄송합니다. 오류가 발생했습니다: Connection failed/)).toBeInTheDocument();
  });

  it('shows empty state when user has no documents', () => {
    render(
      <ChatContainer userHasDocuments={false} />,
      { wrapper: createWrapper() }
    );

    // Should show empty state instead of chat interface
    expect(screen.queryByPlaceholderText(/적성 분석에 대해 궁금한 것을 물어보세요/)).not.toBeInTheDocument();
  });
});