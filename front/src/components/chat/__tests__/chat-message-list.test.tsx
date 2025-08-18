import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChatMessageList } from '../chat-message-list';
import { ChatMessage } from '@/lib/types';


// Mock the feedback hook
vi.mock('@/hooks/use-feedback', () => ({
  useFeedback: vi.fn(() => ({
    submitFeedback: vi.fn(),
    hasFeedback: vi.fn(() => false),
    isSubmitting: false,
  })),
}));

// Mock the toast hook and ToastContainer
vi.mock('@/components/ui/toast', () => ({
  useToast: vi.fn(() => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
  })),
  ToastContainer: vi.fn(() => null),
}));

// Test wrapper with providers
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

// Mock the auto-scroll behavior
const mockScrollIntoView = vi.fn();
Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
  configurable: true,
  value: mockScrollIntoView,
});

describe('ChatMessageList', () => {
  const mockMessages: ChatMessage[] = [
    {
      id: '1',
      type: 'user',
      content: 'First message',
      timestamp: new Date('2024-01-01T10:00:00Z')
    },
    {
      id: '2',
      type: 'assistant',
      content: 'First response',
      timestamp: new Date('2024-01-01T10:01:00Z'),
      confidence_score: 0.8
    }
  ];

  beforeEach(() => {
    mockScrollIntoView.mockClear();
  });

  it('renders empty state when no messages', () => {
    render(
      <TestWrapper>
        <ChatMessageList messages={[]} />
      </TestWrapper>
    );
    
    expect(screen.getByText('💬')).toBeInTheDocument();
    expect(screen.getByText(/안녕하세요! 적성 분석에 대해/)).toBeInTheDocument();
  });

  it('renders messages correctly', () => {
    render(
      <TestWrapper>
        <ChatMessageList messages={mockMessages} />
      </TestWrapper>
    );
    
    expect(screen.getByText('First message')).toBeInTheDocument();
    expect(screen.getByText('First response')).toBeInTheDocument();
  });

  it('shows typing indicator when isTyping is true', () => {
    render(
      <TestWrapper>
        <ChatMessageList 
          messages={mockMessages} 
          isTyping={true}
          typingStatus="processing"
        />
      </TestWrapper>
    );
    
    expect(screen.getByText('질문을 분석하고 있습니다...')).toBeInTheDocument();
  });

  it('shows different typing status messages', () => {
    const { rerender } = render(
      <TestWrapper>
        <ChatMessageList 
          messages={[]} 
          isTyping={true}
          typingStatus="generating"
        />
      </TestWrapper>
    );
    
    expect(screen.getByText('답변을 생성하고 있습니다...')).toBeInTheDocument();
    
    rerender(
      <TestWrapper>
        <ChatMessageList 
          messages={[]} 
          isTyping={true}
          typingStatus="processing"
        />
      </TestWrapper>
    );
    
    expect(screen.getByText('질문을 분석하고 있습니다...')).toBeInTheDocument();
  });

  it('auto-scrolls when new messages are added', async () => {
    const { rerender } = render(
      <TestWrapper>
        <ChatMessageList messages={[mockMessages[0]]} />
      </TestWrapper>
    );
    
    // Add a new message
    rerender(
      <TestWrapper>
        <ChatMessageList messages={mockMessages} />
      </TestWrapper>
    );
    
    // Wait for the timeout in useEffect
    await new Promise(resolve => setTimeout(resolve, 150));
    
    expect(mockScrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'end'
    });
  });

  it('auto-scrolls when typing indicator appears', async () => {
    const { rerender } = render(
      <TestWrapper>
        <ChatMessageList messages={mockMessages} />
      </TestWrapper>
    );
    
    rerender(
      <TestWrapper>
        <ChatMessageList messages={mockMessages} isTyping={true} />
      </TestWrapper>
    );
    
    // Wait for the timeout in useEffect
    await new Promise(resolve => setTimeout(resolve, 150));
    
    expect(mockScrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'end'
    });
  });

  it('applies custom className', () => {
    const { container } = render(
      <TestWrapper>
        <ChatMessageList 
          messages={[]} 
          className="custom-class"
        />
      </TestWrapper>
    );
    
    expect(container.firstChild).toHaveClass('custom-class');
  });
});