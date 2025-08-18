import { SimpleChatHandler, createSimpleChatHandler, sendQuestionSimple } from '../simple-chat-handler';
import { ApiClient } from '../api';

// Mock the ApiClient
jest.mock('../api', () => ({
  ApiClient: {
    sendQuestion: jest.fn()
  }
}));

// Mock user-utils
jest.mock('../user-utils', () => ({
  extractUserId: jest.fn()
}));

const mockApiClient = ApiClient as jest.Mocked<typeof ApiClient>;
const mockExtractUserId = require('../user-utils').extractUserId as jest.MockedFunction<any>;

describe('SimpleChatHandler', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('SimpleChatHandler class', () => {
    it('should create handler with default config', () => {
      const handler = new SimpleChatHandler();
      expect(handler).toBeInstanceOf(SimpleChatHandler);
      expect(handler.getConfig()).toEqual({
        enableDebugLogging: true,
        timeout: 30000,
        maxRetries: 2,
        retryDelay: 1000
      });
    });

    it('should create handler with custom config', () => {
      const config = {
        enableDebugLogging: false,
        timeout: 10000,
        maxRetries: 1,
        retryDelay: 500
      };
      const handler = new SimpleChatHandler(config);
      expect(handler.getConfig()).toEqual(config);
    });

    it('should reject empty questions', async () => {
      const handler = new SimpleChatHandler();
      const result = await handler.sendQuestion('', 'conv-123', 'user-123');
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('Question cannot be empty');
    });

    it('should reject requests without user ID', async () => {
      const handler = new SimpleChatHandler();
      const result = await handler.sendQuestion('Test question', 'conv-123');
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('User ID is required for chat requests');
    });

    it('should prevent duplicate requests', async () => {
      const handler = new SimpleChatHandler();
      
      // Mock a slow API call
      mockApiClient.sendQuestion.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          conversation_id: 'conv-123',
          response: 'Test response',
          confidence_score: 0.9,
          processing_time: 1000,
          retrieved_documents: []
        }), 100))
      );

      // Start first request
      const promise1 = handler.sendQuestion('Test question', 'conv-123', 'user-123');
      
      // Try to start second request immediately
      const result2 = await handler.sendQuestion('Test question 2', 'conv-123', 'user-123');
      
      // Second request should be blocked
      expect(result2.success).toBe(false);
      expect(result2.error).toBe('Already processing a message. Please wait.');
      
      // Wait for first request to complete
      await promise1;
    });

    it('should successfully send question via API', async () => {
      const mockResponse = {
        conversation_id: 'conv-123',
        response: 'Test response',
        confidence_score: 0.9,
        processing_time: 1000,
        retrieved_documents: []
      };

      mockApiClient.sendQuestion.mockResolvedValue(mockResponse);

      const onMessage = jest.fn();
      const handler = new SimpleChatHandler({}, { onMessage });
      
      const result = await handler.sendQuestion('Test question', 'conv-123', 'user-123');
      
      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockResponse);
      expect(mockApiClient.sendQuestion).toHaveBeenCalledWith('Test question', 'conv-123', 'user-123');
      expect(onMessage).toHaveBeenCalledWith(expect.objectContaining({
        type: 'assistant',
        content: 'Test response',
        conversation_id: 'conv-123'
      }));
    });

    it('should handle API errors with retry', async () => {
      const error = new Error('Network error');
      mockApiClient.sendQuestion
        .mockRejectedValueOnce(error)
        .mockResolvedValueOnce({
          conversation_id: 'conv-123',
          response: 'Test response',
          confidence_score: 0.9,
          processing_time: 1000,
          retrieved_documents: []
        });

      const handler = new SimpleChatHandler({ maxRetries: 2, retryDelay: 10 });
      const result = await handler.sendQuestion('Test question', 'conv-123', 'user-123');
      
      expect(result.success).toBe(true);
      expect(mockApiClient.sendQuestion).toHaveBeenCalledTimes(2);
    });

    it('should not retry on auth errors', async () => {
      const error = { status: 401, message: 'Unauthorized' };
      mockApiClient.sendQuestion.mockRejectedValue(error);

      const handler = new SimpleChatHandler({ maxRetries: 2 });
      const result = await handler.sendQuestion('Test question', 'conv-123', 'user-123');
      
      expect(result.success).toBe(false);
      expect(mockApiClient.sendQuestion).toHaveBeenCalledTimes(1);
    });
  });

  describe('createSimpleChatHandler', () => {
    it('should create handler with callbacks and config', () => {
      const onMessage = jest.fn();
      const config = { enableDebugLogging: false };
      
      const handler = createSimpleChatHandler({ onMessage }, config);
      
      expect(handler).toBeInstanceOf(SimpleChatHandler);
      expect(handler.getConfig()).toEqual(expect.objectContaining(config));
    });
  });

  describe('sendQuestionSimple', () => {
    it('should extract user ID and send question', async () => {
      const mockUser = { id: 'user-123' };
      mockExtractUserId.mockReturnValue('user-123');
      mockApiClient.sendQuestion.mockResolvedValue({
        conversation_id: 'conv-123',
        response: 'Test response',
        confidence_score: 0.9,
        processing_time: 1000,
        retrieved_documents: []
      });

      const result = await sendQuestionSimple('Test question', mockUser, 'conv-123');
      
      expect(result.success).toBe(true);
      expect(mockExtractUserId).toHaveBeenCalledWith(mockUser);
      expect(mockApiClient.sendQuestion).toHaveBeenCalledWith('Test question', 'conv-123', 'user-123');
    });

    it('should handle missing user ID', async () => {
      const mockUser = {};
      mockExtractUserId.mockReturnValue(null);

      const result = await sendQuestionSimple('Test question', mockUser);
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('User ID could not be extracted from user object');
    });
  });
});