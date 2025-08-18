import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ChatContainer } from '../chat-container-improved';
import { useAuth } from '@/providers/auth-provider';
import { useSimpleChat } from '@/hooks/use-simple-chat-improved';
import { useDocumentPanel } from '@/hooks/use-document-panel';
import { ChatMessage } from '@/lib/types';

// Mock dependencies
vi.mock('@/providers/auth-provider');
vi.mock('@/hooks/use-simple-chat-improved');
vi.mock('@/hooks/use-document-panel');
vi.mock('@/lib/debug-utils', () => ({
  exposeDebugFunctions: vi.fn(),
  autoDebugOnError: vi.fn(),
}));
vi.mock('@/lib/user-utils', () => ({
  extractUserId: vi.fn((user) => user?.id || user?.user_id),
  getUserIdDebugInfo: vi.fn(() => ({ hasUser: true })),
}));

const mockUseAuth = vi.mocked(useAuth);
const mockUseSimpleChat = vi.mocked(useSimpleChat);
const mockUseDocumentPanel = vi.mocked(useDocumentPanel);

describe('ChatContainer Response Handling', () => {
  const mockUser = {
    id: 'test-user-123',
    name: 'Test User',
    type: 'personal' as const,
  };

  const mockDocumentPanel = {
    documents: [],
    hasDocuments: false,
    isCollapsed: false,
    isMobile: false,
    toggleCollapsed: vi.fn(),
    updateDocuments: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockUseAuth.mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    mockUseDocumentPanel.mockReturnValue(mockDocumentPanel);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Message Deduplication', () => {
    it('should not add duplicate messages to the chat', async () => {
      const mockSendQuestion = vi.fn();
      const mockClearError = vi.fn();
      
      // Create a message that will be returned twice
      const testMessage: ChatMessage = {
        id: 'test-message-1',
        type: 'assistant',
        content: 'Test response',
        timestamp: new Date(),
        conversation_id: 'conv-123',
      };

      let messageCallback: ((message: ChatMessage) => void) | undefined;

      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: false,
        lastMessage: null,
        lastError: null,
        clearError: mockClearError,
        isReady: true,
      });

      const { rerender } = render(
        <ChatContainer userHasDocuments={true} />
      );

      // Simulate receiving the same message twice
      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: false,
        lastMessage: testMessage,
        lastError: null,
        clearError: mockClearError,
        isReady: true,
      });

      rerender(<ChatContainer userHasDocuments={true} />);

      // Wait for message to be processed
      await waitFor(() => {
        const messages = screen.queryAllByText('Test response');
        expect(messages).toHaveLength(1); // Should only appear once
      });

      // Simulate receiving the same message again
      rerender(<ChatContainer userHasDocuments={true} />);

      await waitFor(() => {
        const messages = screen.queryAllByText('Test response');
        expect(messages).toHaveLength(1); // Should still only appear once
      });
    });

    it('should handle messages with different IDs but same content', async () => {
      const mockSendQuestion = vi.fn();
      const mockClearError = vi.fn();
      
      const testMessage1: ChatMessage = {
        id: 'test-message-1',
        type: 'assistant',
        content: 'Same content',
        timestamp: new Date(),
        conversation_id: 'conv-123',
      };

      const testMessage2: ChatMessage = {
        id: 'test-message-2',
        type: 'assistant',
        content: 'Same content',
        timestamp: new Date(Date.now() + 100), // Slightly different timestamp
        conversation_id: 'conv-123',
      };

      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: false,
        lastMessage: testMessage1,
        lastError: null,
        clearError: mockClearError,
        isReady: true,
      });

      const { rerender } = render(
        <ChatContainer userHasDocuments={true} />
      );

      await waitFor(() => {
        expect(screen.getByText('Same content')).toBeInTheDocument();
      });

      // Simulate receiving message with same content but different ID
      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: false,
        lastMessage: testMessage2,
        lastError: null,
        clearError: mockClearError,
        isReady: true,
      });

      rerender(<ChatContainer userHasDocuments={true} />);

      await waitFor(() => {
        const messages = screen.queryAllByText('Same content');
        expect(messages).toHaveLength(1); // Should still only appear once due to content deduplication
      });
    });
  });

  describe('Error Handling', () => {
    it('should display errors without adding them as chat messages', async () => {
      const mockSendQuestion = vi.fn();
      const mockClearError = vi.fn();

      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: false,
        lastMessage: null,
        lastError: 'Test error message',
        clearError: mockClearError,
        isReady: true,
      });

      render(<ChatContainer userHasDocuments={true} />);

      // Error should be displayed in error display area
      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toBeInTheDocument();
        expect(screen.getByText(/Test error message/)).toBeInTheDocument();
      });

      // Error should not appear in chat messages
      const chatMessages = screen.getByTestId('chat-messages');
      expect(chatMessages).not.toHaveTextContent('Test error message');
    });

    it('should allow clearing errors', async () => {
      const mockSendQuestion = vi.fn();
      const mockClearError = vi.fn();

      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: false,
        lastMessage: null,
        lastError: 'Test error message',
        clearError: mockClearError,
        isReady: true,
      });

      render(<ChatContainer userHasDocuments={true} />);

      await waitFor(() => {
        expect(screen.getByTestId('error-display')).toBeInTheDocument();
      });

      // Click the close button
      const closeButton = screen.getByLabelText('오류 메시지 닫기');
      fireEvent.click(closeButton);

      expect(mockClearError).toHaveBeenCalledTimes(1);
    });
  });

  describe('Response Processing', () => {
    it('should properly process API responses and update conversation ID', async () => {
      const mockSendQuestion = vi.fn();
      const mockClearError = vi.fn();
      
      const testMessage: ChatMessage = {
        id: 'response-123',
        type: 'assistant',
        content: 'API response content',
        timestamp: new Date(),
        conversation_id: 'new-conv-456',
        confidence_score: 0.95,
        processing_time: 1500,
        retrieved_documents: [
          {
            id: 'doc-1',
            type: 'aptitude',
            title: 'Test Document',
            preview: 'Document preview',
            relevance_score: 0.8,
          },
        ],
      };

      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: false,
        lastMessage: testMessage,
        lastError: null,
        clearError: mockClearError,
        isReady: true,
      });

      render(<ChatContainer userHasDocuments={true} showDocumentPanel={true} />);

      await waitFor(() => {
        expect(screen.getByText('API response content')).toBeInTheDocument();
      });

      // Verify document panel was updated
      expect(mockDocumentPanel.updateDocuments).toHaveBeenCalledWith(testMessage.retrieved_documents);
    });

    it('should handle responses without retrieved documents', async () => {
      const mockSendQuestion = vi.fn();
      const mockClearError = vi.fn();
      
      const testMessage: ChatMessage = {
        id: 'response-124',
        type: 'assistant',
        content: 'Response without documents',
        timestamp: new Date(),
        conversation_id: 'conv-789',
      };

      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: false,
        lastMessage: testMessage,
        lastError: null,
        clearError: mockClearError,
        isReady: true,
      });

      render(<ChatContainer userHasDocuments={true} showDocumentPanel={true} />);

      await waitFor(() => {
        expect(screen.getByText('Response without documents')).toBeInTheDocument();
      });

      // Document panel should not be updated with undefined documents
      expect(mockDocumentPanel.updateDocuments).not.toHaveBeenCalled();
    });
  });

  describe('State Management', () => {
    it('should prevent message sending when already processing', async () => {
      const mockSendQuestion = vi.fn();
      const mockClearError = vi.fn();

      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: true, // Currently processing
        lastMessage: null,
        lastError: null,
        clearError: mockClearError,
        isReady: true,
      });

      render(<ChatContainer userHasDocuments={true} />);

      const input = screen.getByPlaceholderText(/적성 분석에 대해 궁금한 것을 물어보세요/);
      const sendButton = screen.getByRole('button', { name: /send/i });

      fireEvent.change(input, { target: { value: 'Test message' } });
      fireEvent.click(sendButton);

      // Should not call sendQuestion when already processing
      expect(mockSendQuestion).not.toHaveBeenCalled();
    });

    it('should show processing status when sending message', async () => {
      const mockSendQuestion = vi.fn();
      const mockClearError = vi.fn();

      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: true,
        lastMessage: null,
        lastError: null,
        clearError: mockClearError,
        isReady: true,
      });

      render(<ChatContainer userHasDocuments={true} />);

      await waitFor(() => {
        expect(screen.getByTestId('typing-indicator')).toBeInTheDocument();
      });
    });

    it('should update placeholder text based on state', async () => {
      const mockSendQuestion = vi.fn();
      const mockClearError = vi.fn();

      // Not ready state
      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: false,
        lastMessage: null,
        lastError: null,
        clearError: mockClearError,
        isReady: false,
      });

      const { rerender } = render(<ChatContainer userHasDocuments={true} />);

      expect(screen.getByPlaceholderText(/로그인이 필요하거나 시스템이 준비 중입니다/)).toBeInTheDocument();

      // Ready state
      mockUseSimpleChat.mockReturnValue({
        sendQuestion: mockSendQuestion,
        isProcessing: false,
        lastMessage: null,
        lastError: null,
        clearError: mockClearError,
        isReady: true,
      });

      rerender(<ChatContainer userHasDocuments={true} />);

      expect(screen.getByPlaceholderText(/적성 분석에 대해 궁금한 것을 물어보세요/)).toBeInTheDocument();
    });
  });
});