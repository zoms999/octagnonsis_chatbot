import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { ChatContainer } from '../chat-container';
import { useAuth } from '@/providers/auth-provider';
import { useWebSocketChat } from '@/hooks/websocket-hooks';
import { useDocumentPanel } from '@/hooks/use-document-panel';

// Mock dependencies
vi.mock('@/providers/auth-provider');
vi.mock('@/hooks/websocket-hooks');
vi.mock('@/hooks/use-document-panel');

const mockUseAuth = useAuth as any;
const mockUseWebSocketChat = useWebSocketChat as any;
const mockUseDocumentPanel = useDocumentPanel as any;

describe('Chat Infinite Loop Prevention', () => {
  const mockSendQuestion = vi.fn();
  const mockUpdateDocuments = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    mockUseAuth.mockReturnValue({
      user: { id: 'user-123', name: 'Test User' },
      isAuthenticated: true,
      isLoading: false,
    });

    mockUseWebSocketChat.mockReturnValue({
      sendQuestion: mockSendQuestion,
      isProcessing: false,
      lastResponse: null,
      lastError: null,
      connectionState: { status: 'connected' },
      isConnected: true,
      rateLimitStatus: {
        canSendMessage: true,
        remainingMessages: 10,
        timeUntilNextMessage: 0,
      },
      usedFallback: false,
    });

    mockUseDocumentPanel.mockReturnValue({
      documents: [],
      isCollapsed: false,
      hasDocuments: false,
      isMobile: false,
      toggleCollapsed: vi.fn(),
      updateDocuments: mockUpdateDocuments,
    });
  });

  it('prevents duplicate message sending when already processing', async () => {
    // Set processing state
    mockUseWebSocketChat.mockReturnValue({
      ...mockUseWebSocketChat(),
      isProcessing: true,
    });

    render(<ChatContainer userHasDocuments={true} />);

    const input = screen.getByTestId('chat-input');
    const sendButton = screen.getByTestId('send-button');

    // Try to send a message while processing
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    // Should not call sendQuestion because already processing
    expect(mockSendQuestion).not.toHaveBeenCalled();
  });

  it('prevents duplicate response processing with same response ID', async () => {
    const testResponse = {
      conversation_id: 'conv-123',
      response: 'Test response',
      retrieved_documents: [],
      confidence_score: 0.8,
      processing_time: 1500,
    };

    // First render with response
    const { rerender } = render(<ChatContainer userHasDocuments={true} />);

    // Update with response
    mockUseWebSocketChat.mockReturnValue({
      ...mockUseWebSocketChat(),
      lastResponse: testResponse,
    });

    rerender(<ChatContainer userHasDocuments={true} />);

    // Wait for response to be processed
    await waitFor(() => {
      expect(screen.getByText('Test response')).toBeInTheDocument();
    });

    // Try to process the same response again
    mockUseWebSocketChat.mockReturnValue({
      ...mockUseWebSocketChat(),
      lastResponse: testResponse, // Same response object
    });

    rerender(<ChatContainer userHasDocuments={true} />);

    // Should only have one message in the list
    const messages = screen.getAllByText('Test response');
    expect(messages).toHaveLength(1);
  });

  it('prevents multiple rapid message submissions', async () => {
    render(<ChatContainer userHasDocuments={true} />);

    const input = screen.getByTestId('chat-input');
    const sendButton = screen.getByTestId('send-button');

    // Send first message
    fireEvent.change(input, { target: { value: 'First message' } });
    fireEvent.click(sendButton);

    // Try to send second message immediately
    fireEvent.change(input, { target: { value: 'Second message' } });
    fireEvent.click(sendButton);

    // Should only call sendQuestion once
    expect(mockSendQuestion).toHaveBeenCalledTimes(1);
    expect(mockSendQuestion).toHaveBeenCalledWith('First message', undefined);
  });

  it('allows new messages after processing completes', async () => {
    const { rerender } = render(<ChatContainer userHasDocuments={true} />);

    const input = screen.getByTestId('chat-input');
    const sendButton = screen.getByTestId('send-button');

    // Send first message
    fireEvent.change(input, { target: { value: 'First message' } });
    fireEvent.click(sendButton);

    expect(mockSendQuestion).toHaveBeenCalledWith('First message', undefined);

    // Simulate processing completion by updating the mock
    mockUseWebSocketChat.mockReturnValue({
      ...mockUseWebSocketChat(),
      isProcessing: false,
      lastResponse: {
        conversation_id: 'conv-123',
        response: 'Response to first message',
        retrieved_documents: [],
        confidence_score: 0.8,
        processing_time: 1500,
      },
    });

    rerender(<ChatContainer userHasDocuments={true} />);

    // Now should be able to send another message
    fireEvent.change(input, { target: { value: 'Second message' } });
    fireEvent.click(sendButton);

    expect(mockSendQuestion).toHaveBeenCalledTimes(2);
    expect(mockSendQuestion).toHaveBeenLastCalledWith('Second message', 'conv-123');
  });

  it('prevents duplicate document panel updates', async () => {
    const testResponse = {
      conversation_id: 'conv-123',
      response: 'Test response',
      retrieved_documents: [{ id: 'doc-1', title: 'Test Doc' }],
      confidence_score: 0.8,
      processing_time: 1500,
    };

    const { rerender } = render(<ChatContainer userHasDocuments={true} showDocumentPanel={true} />);

    // Update with response containing documents
    mockUseWebSocketChat.mockReturnValue({
      ...mockUseWebSocketChat(),
      lastResponse: testResponse,
    });

    rerender(<ChatContainer userHasDocuments={true} showDocumentPanel={true} />);

    // Wait for processing
    await waitFor(() => {
      expect(mockUpdateDocuments).toHaveBeenCalledTimes(1);
    });

    // Try to process the same response again
    rerender(<ChatContainer userHasDocuments={true} showDocumentPanel={true} />);

    // Should not call updateDocuments again for the same response
    expect(mockUpdateDocuments).toHaveBeenCalledTimes(1);
  });
});