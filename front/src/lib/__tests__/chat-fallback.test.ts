import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ChatFallbackHandler, EnhancedChatHandler } from '../chat-fallback';
import { ApiClient } from '../api';

// Mock ApiClient
vi.mock('../api', () => ({
  ApiClient: {
    sendQuestion: vi.fn(),
  },
}));

describe('ChatFallbackHandler', () => {
  let handler: ChatFallbackHandler;

  beforeEach(() => {
    vi.useFakeTimers();
    handler = new ChatFallbackHandler({
      maxRetries: 3,
      retryDelay: 1000,
      timeout: 5000
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('WebSocket availability management', () => {
    it('should initialize with WebSocket available', () => {
      expect(handler.shouldUseFallback()).toBe(false);
    });

    it('should use fallback when WebSocket is unavailable', () => {
      handler.setWebSocketAvailable(false);
      expect(handler.shouldUseFallback()).toBe(true);
    });

    it('should deactivate fallback when WebSocket becomes available', () => {
      handler.activateFallback();
      expect(handler.shouldUseFallback()).toBe(true);

      handler.setWebSocketAvailable(true);
      expect(handler.shouldUseFallback()).toBe(false);
    });

    it('should manually activate and deactivate fallback', () => {
      handler.activateFallback();
      expect(handler.shouldUseFallback()).toBe(true);

      handler.deactivateFallback();
      expect(handler.shouldUseFallback()).toBe(false);
    });
  });

  describe('HTTP fallback requests', () => {
    it('should send question via HTTP successfully', async () => {
      const mockResponse = {
        conversation_id: 'conv-123',
        response: 'Test response',
        retrieved_documents: [],
        confidence_score: 0.8,
        processing_time: 1500,
        timestamp: new Date().toISOString()
      };

      (ApiClient.sendQuestion as any).mockResolvedValue(mockResponse);

      const result = await handler.sendQuestionHTTP(
        'What is my aptitude?',
        'conv-123',
        'user-123'
      );

      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockResponse);
      expect(result.usedFallback).toBe(true);
      expect(ApiClient.sendQuestion).toHaveBeenCalledWith(
        'What is my aptitude?',
        'conv-123'
      );
    });

    it('should handle missing user ID', async () => {
      const result = await handler.sendQuestionHTTP('Test question');

      expect(result.success).toBe(false);
      expect(result.error).toBe('User ID is required for HTTP fallback');
      expect(result.usedFallback).toBe(true);
    });

    it('should retry on network errors', async () => {
      (ApiClient.sendQuestion as any)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValue({
          conversation_id: 'conv-123',
          response: 'Success after retries'
        });

      const resultPromise = handler.sendQuestionHTTP(
        'Test question',
        undefined,
        'user-123'
      );

      // Advance timers to handle retry delays
      await vi.advanceTimersByTimeAsync(3000);

      const result = await resultPromise;
      expect(result.success).toBe(true);
      expect(ApiClient.sendQuestion).toHaveBeenCalledTimes(3);
    });

    it('should not retry on auth errors', async () => {
      const authError = new Error('Unauthorized');
      (authError as any).status = 401;
      (ApiClient.sendQuestion as any).mockRejectedValue(authError);

      const result = await handler.sendQuestionHTTP(
        'Test question',
        undefined,
        'user-123'
      );

      expect(result.success).toBe(false);
      expect(result.error).toBe('Unauthorized');
      expect(ApiClient.sendQuestion).toHaveBeenCalledTimes(1); // No retries
    });

    it('should handle timeout', async () => {
      // Mock a request that times out
      const timeoutError = new Error('Request timeout');
      timeoutError.name = 'AbortError';
      (ApiClient.sendQuestion as any).mockRejectedValue(timeoutError);

      const resultPromise = handler.sendQuestionHTTP(
        'Test question',
        undefined,
        'user-123'
      );

      // Advance timers to handle retries
      await vi.advanceTimersByTimeAsync(5000);

      const result = await resultPromise;
      expect(result.success).toBe(false);
      expect(result.error).toBe('Request timeout');
    }, 10000);

    it('should implement exponential backoff for retries', async () => {
      (ApiClient.sendQuestion as any).mockRejectedValue(new Error('Network error'));

      const resultPromise = handler.sendQuestionHTTP(
        'Test question',
        undefined,
        'user-123'
      );

      // Advance timers to handle all retries
      await vi.advanceTimersByTimeAsync(7000);

      const result = await resultPromise;
      expect(result.success).toBe(false);
      expect(ApiClient.sendQuestion).toHaveBeenCalledTimes(3);
    });
  });

  describe('status management', () => {
    it('should return correct status', () => {
      let status = handler.getStatus();
      expect(status.isWebSocketAvailable).toBe(true);
      expect(status.fallbackActive).toBe(false);
      expect(status.shouldUseFallback).toBe(false);

      handler.setWebSocketAvailable(false);
      status = handler.getStatus();
      expect(status.isWebSocketAvailable).toBe(false);
      expect(status.shouldUseFallback).toBe(true);

      handler.activateFallback();
      status = handler.getStatus();
      expect(status.fallbackActive).toBe(true);
    });
  });
});

describe('EnhancedChatHandler', () => {
  let handler: EnhancedChatHandler;
  let mockCallbacks: {
    onMessage: ReturnType<typeof vi.fn>;
    onError: ReturnType<typeof vi.fn>;
    onFallbackUsed: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.useFakeTimers();
    mockCallbacks = {
      onMessage: vi.fn(),
      onError: vi.fn(),
      onFallbackUsed: vi.fn(),
    };

    handler = new EnhancedChatHandler(
      { maxRetries: 2, retryDelay: 500, timeout: 3000 },
      mockCallbacks
    );

    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('WebSocket integration', () => {
    it('should send via WebSocket when available', async () => {
      const mockWebSocketSend = vi.fn();
      
      await handler.sendQuestion(
        'Test question',
        'conv-123',
        'user-123',
        mockWebSocketSend
      );

      expect(mockWebSocketSend).toHaveBeenCalledWith({
        type: 'question',
        data: {
          question: 'Test question',
          conversation_id: 'conv-123'
        },
        timestamp: expect.any(String)
      });
    });

    it('should fallback to HTTP when WebSocket send fails', async () => {
      const mockWebSocketSend = vi.fn().mockImplementation(() => {
        throw new Error('WebSocket send failed');
      });

      const mockResponse = {
        conversation_id: 'conv-123',
        response: 'Fallback response',
        retrieved_documents: [],
        confidence_score: 0.7,
        processing_time: 2000,
        timestamp: new Date().toISOString()
      };

      (ApiClient.sendQuestion as any).mockResolvedValue(mockResponse);

      await handler.sendQuestion(
        'Test question',
        'conv-123',
        'user-123',
        mockWebSocketSend
      );

      expect(mockWebSocketSend).toHaveBeenCalled();
      expect(ApiClient.sendQuestion).toHaveBeenCalled();
      expect(mockCallbacks.onMessage).toHaveBeenCalledWith({
        type: 'response',
        data: mockResponse,
        timestamp: expect.any(String)
      });
      expect(mockCallbacks.onFallbackUsed).toHaveBeenCalledWith('WebSocket send failed');
    });

    it('should use HTTP when WebSocket is unavailable', async () => {
      handler.onWebSocketStatusChange(false);

      const mockResponse = {
        conversation_id: 'conv-123',
        response: 'HTTP response',
        retrieved_documents: [],
        confidence_score: 0.9,
        processing_time: 1000,
        timestamp: new Date().toISOString()
      };

      (ApiClient.sendQuestion as any).mockResolvedValue(mockResponse);

      await handler.sendQuestion(
        'Test question',
        'conv-123',
        'user-123'
      );

      expect(ApiClient.sendQuestion).toHaveBeenCalled();
      expect(mockCallbacks.onMessage).toHaveBeenCalled();
      expect(mockCallbacks.onFallbackUsed).toHaveBeenCalledWith('WebSocket unavailable');
    });
  });

  describe('error handling', () => {
    it('should call onError when HTTP request fails', async () => {
      handler.onWebSocketStatusChange(false);
      (ApiClient.sendQuestion as any).mockRejectedValue(new Error('HTTP request failed'));

      const sendPromise = handler.sendQuestion(
        'Test question',
        'conv-123',
        'user-123'
      );

      // Advance timers to handle retries
      await vi.advanceTimersByTimeAsync(5000);
      await sendPromise;

      expect(mockCallbacks.onError).toHaveBeenCalledWith('HTTP request failed');
    });

    it('should handle network errors gracefully', async () => {
      handler.onWebSocketStatusChange(false);
      
      const networkError = new Error('Network error');
      (ApiClient.sendQuestion as any).mockRejectedValue(networkError);

      const sendPromise = handler.sendQuestion(
        'Test question',
        undefined,
        'user-123'
      );

      // Advance timers to handle retries
      await vi.advanceTimersByTimeAsync(5000);
      await sendPromise;

      expect(mockCallbacks.onError).toHaveBeenCalled();
    });
  });

  describe('status management', () => {
    it('should track WebSocket status changes', () => {
      handler.onWebSocketStatusChange(true);
      let status = handler.getStatus();
      expect(status.isWebSocketAvailable).toBe(true);

      handler.onWebSocketStatusChange(false);
      status = handler.getStatus();
      expect(status.isWebSocketAvailable).toBe(false);
    });

    it('should allow manual fallback control', () => {
      handler.forceFallback();
      let status = handler.getStatus();
      expect(status.fallbackActive).toBe(true);

      handler.disableFallback();
      status = handler.getStatus();
      expect(status.fallbackActive).toBe(false);
    });
  });

  describe('message conversion', () => {
    it('should convert HTTP response to WebSocket message format', async () => {
      handler.onWebSocketStatusChange(false);

      const httpResponse = {
        conversation_id: 'conv-123',
        response: 'Test response',
        retrieved_documents: [
          {
            id: 'doc-1',
            type: 'aptitude',
            title: 'Test Document',
            preview: 'Preview text',
            relevance_score: 0.8
          }
        ],
        confidence_score: 0.85,
        processing_time: 1200,
        timestamp: '2023-01-01T00:00:00Z'
      };

      (ApiClient.sendQuestion as any).mockResolvedValue(httpResponse);

      await handler.sendQuestion(
        'Test question',
        'conv-123',
        'user-123'
      );

      expect(mockCallbacks.onMessage).toHaveBeenCalledWith({
        type: 'response',
        data: httpResponse,
        timestamp: expect.any(String)
      });
    });
  });
});