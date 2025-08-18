import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect } from 'vitest';
import { ChatBubble } from '../chat-bubble';
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

describe('ChatBubble', () => {
  const mockUserMessage: ChatMessage = {
    id: '1',
    type: 'user',
    content: 'Hello, this is a user message',
    timestamp: new Date('2024-01-01T10:00:00Z')
  };

  const mockAssistantMessage: ChatMessage = {
    id: '2',
    type: 'assistant',
    content: 'Hello, this is an assistant response',
    timestamp: new Date('2024-01-01T10:01:00Z'),
    confidence_score: 0.85,
    processing_time: 2.5,
    retrieved_documents: [
      {
        id: 'doc1',
        type: 'aptitude',
        title: 'Test Document',
        preview: 'Test preview',
        relevance_score: 0.9
      }
    ]
  };

  it('renders user message correctly', () => {
    render(
      <TestWrapper>
        <ChatBubble message={mockUserMessage} />
      </TestWrapper>
    );
    
    expect(screen.getByText('Hello, this is a user message')).toBeInTheDocument();
    expect(screen.getByText('오후 07:00')).toBeInTheDocument();
  });

  it('renders assistant message with metadata', () => {
    render(
      <TestWrapper>
        <ChatBubble message={mockAssistantMessage} />
      </TestWrapper>
    );
    
    expect(screen.getByText('Hello, this is an assistant response')).toBeInTheDocument();
    expect(screen.getByText('신뢰도:')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('처리시간:')).toBeInTheDocument();
    expect(screen.getByText('2.50초')).toBeInTheDocument();
    expect(screen.getByText('참조문서:')).toBeInTheDocument();
    expect(screen.getByText('1개')).toBeInTheDocument();
  });

  it('applies correct styling for user messages', () => {
    const { container } = render(
      <TestWrapper>
        <ChatBubble message={mockUserMessage} />
      </TestWrapper>
    );
    
    const messageContainer = container.querySelector('.justify-end');
    expect(messageContainer).toBeInTheDocument();
    
    const messageBubble = container.querySelector('.bg-blue-600');
    expect(messageBubble).toBeInTheDocument();
  });

  it('applies correct styling for assistant messages', () => {
    const { container } = render(
      <TestWrapper>
        <ChatBubble message={mockAssistantMessage} />
      </TestWrapper>
    );
    
    const messageContainer = container.querySelector('.justify-start');
    expect(messageContainer).toBeInTheDocument();
    
    const messageBubble = container.querySelector('.bg-gray-100');
    expect(messageBubble).toBeInTheDocument();
  });

  it('shows confidence score with appropriate color', () => {
    const highConfidenceMessage = {
      ...mockAssistantMessage,
      confidence_score: 0.9
    };
    
    const { container } = render(
      <TestWrapper>
        <ChatBubble message={highConfidenceMessage} />
      </TestWrapper>
    );
    
    const confidenceBar = container.querySelector('.bg-green-500');
    expect(confidenceBar).toBeInTheDocument();
  });

  it('handles message without metadata gracefully', () => {
    const simpleAssistantMessage: ChatMessage = {
      id: '3',
      type: 'assistant',
      content: 'Simple response',
      timestamp: new Date('2024-01-01T10:02:00Z')
    };
    
    render(
      <TestWrapper>
        <ChatBubble message={simpleAssistantMessage} />
      </TestWrapper>
    );
    
    expect(screen.getByText('Simple response')).toBeInTheDocument();
    expect(screen.queryByText('신뢰도:')).not.toBeInTheDocument();
    expect(screen.queryByText('처리시간:')).not.toBeInTheDocument();
    expect(screen.queryByText('참조문서:')).not.toBeInTheDocument();
  });
});