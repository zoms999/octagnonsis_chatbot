import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SimpleChatHandler } from '@/lib/simple-chat-handler';
import { ChatMessage } from '@/lib/types';

// Mock the API client
vi.mock('@/lib/api', () => ({
  ApiClient: {
    sendQuestion: vi.fn(),
  },
}));

import { ApiClient } from '@/lib/api';

const mockApiClient = vi.mocked(ApiClient);

describe('Response Handling and State Management', () => {
  let chatHandler: SimpleChatHandler;
  let mockCallbacks: {
    onMessage: ReturnType<typeof vi.fn>;
    onError: ReturnType<typeof vi.fn>;
    onProcessingStart: ReturnType<typeof vi.fn>;
    onProcessingEnd: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockCallbacks = {
      onMessage: vi.fn(),
      onError: vi.fn(),
      onProcessingStart: vi.fn(),
      onProcessingEnd: vi.fn(),
    };

    chatHandler = new SimpleChatHandler(
      { enableDebugLogging: false },
      mockCallbacks
    );
  });

  describe('API Response Processing', () => {
    it('should properly convert API response to ChatMessage format', async () => {
      const mockApiResponse = {
        conversation_id: 'conv-123',
        response: 'Test AI response',
        retrieved_documents: [
          {
            id: 'doc-1',
            type: 'aptitude',
            title: 'Test Document',
            preview: 'Document preview',
            relevance_score: 0.8,
          },
        ],
        confidence_score: 0.95,
        processing_time: 1500,
        timestamp: '2024-01-01T12:00:00Z',
      };

      mockApiClient.sendQuestion.mockResolvedValueOnce(mockApiResponse);

      const result = await chatHandler.sendQuestion('Test question', 'conv-123', 'user-123');

      expect(result.success).toBe(true);
      expect(mockCallbacks.onProcessingStart).toHaveBeenCalledTimes(1);
      expect(mockCallbacks.onProcessingEnd).toHaveBeenCalledTimes(1);
      expect(mockCallbacks.onMessage).toHaveBeenCalledTimes(1);

      const receivedMessage = mockCallbacks.onMessage.mock.calls[0][0] as ChatMessage;
      expect(receivedMessage.type).toBe('assistant');
      expect(receivedMessage.content).toBe('Test AI response');
      expect(receivedMessage.conversation_id).toBe('conv-123');
      expect(receivedMessage.confidence_score).toBe(0.95);
      expect(receivedMessage.processing_time).toBe(1500);
      expect(receivedMessage.retrieved_documents).toHaveLength(1);
      expect(receivedMessage.timestamp).toBeInstanceOf(Date);
    });

    it('should handle API responses without optional fields', async () => {
      const mockApiResponse = {
        conversation_id: 'conv-456',
        response: 'Simple response',
        retrieved_documents: [],
        confidence_score: null,
        processing_time: null,
        timestamp: null,
      };

      mockApiClient.sendQuestion.mockResolvedValueOnce(mockApiResponse);

      const result = await chatHandler.sendQuestion('Test question', 'conv-456', 'user-123');

      expect(result.success).toBe(true);
      expect(mockCallbacks.onMessage).toHaveBeenCalledTimes(1);

      const receivedMessage = mockCallbacks.onMessage.mock.calls[0][0] as ChatMessage;
      expect(receivedMessage.type).toBe('assistant');
      expect(receivedMessage.content).toBe('Simple response');
      expect(receivedMessage.conversation_id).toBe('conv-456');
      expect(receivedMessage.confidence_score).toBeUndefined();
      expect(receivedMessage.processing_time).toBeUndefined();
      expect(receivedMessage.retrieved_documents).toEqual([]);
      expect(receivedMessage.timestamp).toBeInstanceOf(Date);
    });

    it('should handle invalid API responses', async () => {
      const mockApiResponse = {
        conversation_id: 'conv-789',
        response: null, // Invalid response
        retrieved_documents: [],
      };

      mockApiClient.sendQuestion.mockResolvedValueOnce(mockApiResponse);

      const result = await chatHandler.sendQuestion('Test question', 'conv-789', 'user-123');

      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid response content');
      expect(mockCallbacks.onError).toHaveBeenCalledTimes(1);
      expect(mockCallbacks.onMessage).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors properly', async () => {
      const apiError = new Error('API request failed');
      mockApiClient.sendQuestion.mockRejectedValueOnce(apiError);

      const result = await chatHandler.sendQuestion('Test question', 'conv-123', 'user-123');

      expect(result.success).toBe(false);
      expect(result.error).toBe('API request failed');
      expect(mockCallbacks.onError).toHaveBeenCalledWith('API request failed');
      expect(mockCallbacks.onMessage).not.toHaveBeenCalled();
    });

    it('should handle network errors with retry', async () => {
      const networkError = new Error('Network error');
      mockApiClient.sendQuestion
        .mockRejectedValueOnce(networkError)
        .mockRejectedValueOnce(networkError)
        .mockResolvedValueOnce({
          conversation_id: 'conv-123',
          response: 'Success after retry',
          retrieved_documents: [],
        });

      const result = await chatHandler.sendQuestion('Test question', 'conv-123', 'user-123');

      expect(result.success).toBe(true);
      expect(mockApiClient.sendQuestion).toHaveBeenCalledTimes(3);
      expect(mockCallbacks.onMessage).toHaveBeenCalledTimes(1);
    });

    it('should not retry on authentication errors', async () => {
      const authError = new Error('Unauthorized');
      authError.status = 401;
      mockApiClient.sendQuestion.mockRejectedValueOnce(authError);

      const result = await chatHandler.sendQuestion('Test question', 'conv-123', 'user-123');

      expect(result.success).toBe(false);
      expect(mockApiClient.sendQuestion).toHaveBeenCalledTimes(1); // No retry
      expect(mockCallbacks.onError).toHaveBeenCalledWith('Unauthorized');
    });
  });

  describe('Message Deduplication', () => {
    it('should prevent duplicate requests', async () => {
      const mockApiResponse = {
        conversation_id: 'conv-123',
        response: 'Test response',
        retrieved_documents: [],
      };

      mockApiClient.sendQuestion.mockResolvedValue(mockApiResponse);

      // Start first request
      const promise1 = chatHandler.sendQuestion('Test question', 'conv-123', 'user-123');
      
      // Try to start second request while first is processing
      const result2 = await chatHandler.sendQuestion('Test question 2', 'conv-123', 'user-123');

      expect(result2.success).toBe(false);
      expect(result2.error).toContain('Already processing');

      // Wait for first request to complete
      const result1 = await promise1;
      expect(result1.success).toBe(true);
    });

    it('should generate unique message IDs', async () => {
      const mockApiResponse = {
        conversation_id: 'conv-123',
        response: 'Test response',
        retrieved_documents: [],
      };

      mockApiClient.sendQuestion.mockResolvedValue(mockApiResponse);

      // Send first message
      await chatHandler.sendQuestion('Test question 1', 'conv-123', 'user-123');
      
      // Send second message after first completes
      await chatHandler.sendQuestion('Test question 2', 'conv-123', 'user-123');

      expect(mockCallbacks.onMessage).toHaveBeenCalledTimes(2);

      const message1 = mockCallbacks.onMessage.mock.calls[0][0] as ChatMessage;
      const message2 = mockCallbacks.onMessage.mock.calls[1][0] as ChatMessage;

      expect(message1.id).not.toBe(message2.id);
      expect(message1.id).toMatch(/^response-\d+-\d+-[a-z0-9]+$/);
      expect(message2.id).toMatch(/^response-\d+-\d+-[a-z0-9]+$/);
    });
  });

  describe('State Management', () => {
    it('should track processing state correctly', async () => {
      const mockApiResponse = {
        conversation_id: 'conv-123',
        response: 'Test response',
        retrieved_documents: [],
      };

      // Delay the API response to test processing state
      mockApiClient.sendQuestion.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve(mockApiResponse), 100))
      );

      expect(chatHandler.isCurrentlyProcessing()).toBe(false);

      const promise = chatHandler.sendQuestion('Test question', 'conv-123', 'user-123');
      
      expect(mockCallbacks.onProcessingStart).toHaveBeenCalledTimes(1);
      expect(chatHandler.isCurrentlyProcessing()).toBe(true);

      await promise;

      expect(mockCallbacks.onProcessingEnd).toHaveBeenCalledTimes(1);
      expect(chatHandler.isCurrentlyProcessing()).toBe(false);
    });

    it('should validate input parameters', async () => {
      // Test empty question
      const result1 = await chatHandler.sendQuestion('', 'conv-123', 'user-123');
      expect(result1.success).toBe(false);
      expect(result1.error).toContain('cannot be empty');

      // Test missing user ID
      const result2 = await chatHandler.sendQuestion('Test question', 'conv-123', '');
      expect(result2.success).toBe(false);
      expect(result2.error).toContain('User ID is required');

      expect(mockCallbacks.onProcessingStart).not.toHaveBeenCalled();
      expect(mockApiClient.sendQuestion).not.toHaveBeenCalled();
    });
  });
});