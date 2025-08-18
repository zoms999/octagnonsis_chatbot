import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { 
  MessageValidator, 
  RateLimiter, 
  WebSocketMessageHandler 
} from '../websocket-handlers';
import { WebSocketMessage } from '../types';

describe('MessageValidator', () => {
  describe('validateQuestionMessage', () => {
    it('should validate valid question message', () => {
      const message = {
        data: {
          question: 'What is my aptitude?',
          conversation_id: 'conv-123'
        }
      };

      const result = MessageValidator.validateQuestionMessage(message);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject message without data', () => {
      const message = {};
      const result = MessageValidator.validateQuestionMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Message data is required');
    });

    it('should reject message without question', () => {
      const message = { data: {} };
      const result = MessageValidator.validateQuestionMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Question is required and must be a string');
    });

    it('should reject empty question', () => {
      const message = { data: { question: '   ' } };
      const result = MessageValidator.validateQuestionMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Question cannot be empty');
    });

    it('should reject question that is too long', () => {
      const message = { data: { question: 'a'.repeat(1001) } };
      const result = MessageValidator.validateQuestionMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Question must be less than 1000 characters');
    });

    it('should reject invalid conversation_id type', () => {
      const message = { 
        data: { 
          question: 'Valid question',
          conversation_id: 123 
        } 
      };
      const result = MessageValidator.validateQuestionMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Conversation ID must be a string');
    });
  });

  describe('validateResponseMessage', () => {
    it('should validate valid response message', () => {
      const message = {
        data: {
          conversation_id: 'conv-123',
          response: 'Your aptitude shows strong analytical skills.',
          confidence_score: 0.85,
          processing_time: 1500
        }
      };

      const result = MessageValidator.validateResponseMessage(message);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject message without required fields', () => {
      const message = { data: {} };
      const result = MessageValidator.validateResponseMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('conversation_id is required');
      expect(result.errors).toContain('response is required');
    });

    it('should reject invalid confidence score', () => {
      const message = {
        data: {
          conversation_id: 'conv-123',
          response: 'Valid response',
          confidence_score: 1.5
        }
      };
      const result = MessageValidator.validateResponseMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Confidence score must be a number between 0 and 1');
    });

    it('should reject negative processing time', () => {
      const message = {
        data: {
          conversation_id: 'conv-123',
          response: 'Valid response',
          processing_time: -100
        }
      };
      const result = MessageValidator.validateResponseMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Processing time must be a non-negative number');
    });
  });

  describe('validateStatusMessage', () => {
    it('should validate valid status message', () => {
      const message = {
        data: {
          status: 'processing',
          progress: 50
        }
      };

      const result = MessageValidator.validateStatusMessage(message);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject invalid status', () => {
      const message = {
        data: {
          status: 'invalid_status'
        }
      };
      const result = MessageValidator.validateStatusMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Status must be one of: processing, generating, complete');
    });

    it('should reject invalid progress value', () => {
      const message = {
        data: {
          status: 'processing',
          progress: 150
        }
      };
      const result = MessageValidator.validateStatusMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Progress must be a number between 0 and 100');
    });
  });

  describe('validateMessage', () => {
    it('should validate complete message structure', () => {
      const message: WebSocketMessage = {
        type: 'question',
        data: {
          question: 'What is my aptitude?'
        },
        timestamp: new Date().toISOString()
      };

      const result = MessageValidator.validateMessage(message);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject message without type or timestamp', () => {
      const message = {
        data: { question: 'Valid question' }
      } as any;

      const result = MessageValidator.validateMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Message type and timestamp are required');
    });

    it('should reject unknown message type', () => {
      const message = {
        type: 'unknown_type',
        data: {},
        timestamp: new Date().toISOString()
      } as any;

      const result = MessageValidator.validateMessage(message);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Unknown message type: unknown_type');
    });
  });
});

describe('RateLimiter', () => {
  let rateLimiter: RateLimiter;

  beforeEach(() => {
    vi.useFakeTimers();
    rateLimiter = new RateLimiter({ maxMessages: 3, windowMs: 60000 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should allow messages within limit', () => {
    expect(rateLimiter.canSendMessage()).toBe(true);
    
    rateLimiter.recordMessage();
    expect(rateLimiter.canSendMessage()).toBe(true);
    
    rateLimiter.recordMessage();
    expect(rateLimiter.canSendMessage()).toBe(true);
    
    rateLimiter.recordMessage();
    expect(rateLimiter.canSendMessage()).toBe(false);
  });

  it('should reset after time window', () => {
    // Fill up the rate limit
    rateLimiter.recordMessage();
    rateLimiter.recordMessage();
    rateLimiter.recordMessage();
    
    expect(rateLimiter.canSendMessage()).toBe(false);
    
    // Advance time past the window
    vi.advanceTimersByTime(61000);
    
    expect(rateLimiter.canSendMessage()).toBe(true);
  });

  it('should calculate remaining messages correctly', () => {
    expect(rateLimiter.getRemainingMessages()).toBe(3);
    
    rateLimiter.recordMessage();
    expect(rateLimiter.getRemainingMessages()).toBe(2);
    
    rateLimiter.recordMessage();
    expect(rateLimiter.getRemainingMessages()).toBe(1);
    
    rateLimiter.recordMessage();
    expect(rateLimiter.getRemainingMessages()).toBe(0);
  });

  it('should calculate time until next message', () => {
    rateLimiter.recordMessage();
    rateLimiter.recordMessage();
    rateLimiter.recordMessage();
    
    const timeUntil = rateLimiter.getTimeUntilNextMessage();
    expect(timeUntil).toBeGreaterThan(0);
    expect(timeUntil).toBeLessThanOrEqual(60000);
  });
});

describe('WebSocketMessageHandler', () => {
  let handler: WebSocketMessageHandler;
  let mockRateLimitCallback: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    mockRateLimitCallback = vi.fn();
    handler = new WebSocketMessageHandler(
      { maxMessages: 2, windowMs: 60000 },
      mockRateLimitCallback
    );
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Message Handling', () => {
    it('should register and call message handlers', () => {
      const mockHandler = vi.fn();
      handler.on('response', mockHandler);

      const message: WebSocketMessage = {
        type: 'response',
        data: {
          conversation_id: 'conv-123',
          response: 'Test response'
        },
        timestamp: new Date().toISOString()
      };

      handler.handleMessage(message);
      expect(mockHandler).toHaveBeenCalledWith(message);
    });

    it('should handle multiple handlers for same event', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();
      
      handler.on('response', handler1);
      handler.on('response', handler2);

      const message: WebSocketMessage = {
        type: 'response',
        data: {
          conversation_id: 'conv-123',
          response: 'Test response'
        },
        timestamp: new Date().toISOString()
      };

      handler.handleMessage(message);
      expect(handler1).toHaveBeenCalledWith(message);
      expect(handler2).toHaveBeenCalledWith(message);
    });

    it('should unsubscribe handlers correctly', () => {
      const mockHandler = vi.fn();
      const unsubscribe = handler.on('response', mockHandler);

      const message: WebSocketMessage = {
        type: 'response',
        data: {
          conversation_id: 'conv-123',
          response: 'Test response'
        },
        timestamp: new Date().toISOString()
      };

      handler.handleMessage(message);
      expect(mockHandler).toHaveBeenCalledTimes(1);

      unsubscribe();
      handler.handleMessage(message);
      expect(mockHandler).toHaveBeenCalledTimes(1); // Should not be called again
    });

    it('should handle wildcard listeners', () => {
      const wildcardHandler = vi.fn();
      handler.on('*', wildcardHandler);

      const message: WebSocketMessage = {
        type: 'response',
        data: {
          conversation_id: 'conv-123',
          response: 'Test response'
        },
        timestamp: new Date().toISOString()
      };

      handler.handleMessage(message);
      expect(wildcardHandler).toHaveBeenCalledWith(message);
    });

    it('should handle invalid messages gracefully', () => {
      const errorHandler = vi.fn();
      handler.on('error', errorHandler);

      const invalidMessage = {
        type: 'question',
        data: {}, // Missing required question field
        timestamp: new Date().toISOString()
      } as WebSocketMessage;

      handler.handleMessage(invalidMessage);
      expect(errorHandler).toHaveBeenCalled();
    });
  });

  describe('Rate Limiting', () => {
    it('should enforce rate limits on outgoing messages', () => {
      const mockSend = vi.fn();
      
      const message: WebSocketMessage = {
        type: 'question',
        data: { question: 'Test question' },
        timestamp: new Date().toISOString()
      };

      // First two messages should succeed
      expect(handler.sendMessage(message, mockSend)).toBe(true);
      expect(handler.sendMessage(message, mockSend)).toBe(true);
      
      // Third message should be rate limited
      expect(handler.sendMessage(message, mockSend)).toBe(false);
      expect(mockRateLimitCallback).toHaveBeenCalled();
    });

    it('should provide rate limit status', () => {
      const status = handler.getRateLimitStatus();
      expect(status).toHaveProperty('canSendMessage');
      expect(status).toHaveProperty('remainingMessages');
      expect(status).toHaveProperty('timeUntilNextMessage');
    });

    it('should not rate limit non-question messages', () => {
      const mockSend = vi.fn();
      
      const statusMessage: WebSocketMessage = {
        type: 'status',
        data: { status: 'processing' },
        timestamp: new Date().toISOString()
      };

      // Should be able to send multiple status messages
      expect(handler.sendMessage(statusMessage, mockSend)).toBe(true);
      expect(handler.sendMessage(statusMessage, mockSend)).toBe(true);
      expect(handler.sendMessage(statusMessage, mockSend)).toBe(true);
      
      expect(mockSend).toHaveBeenCalledTimes(3);
    });
  });

  describe('Utility Methods', () => {
    it('should clear all handlers', () => {
      handler.on('response', vi.fn());
      handler.on('error', vi.fn());
      
      expect(handler.getHandlerCount('response')).toBe(1);
      expect(handler.getHandlerCount('error')).toBe(1);
      
      handler.clearHandlers();
      
      expect(handler.getHandlerCount('response')).toBe(0);
      expect(handler.getHandlerCount('error')).toBe(0);
    });

    it('should return handler counts', () => {
      handler.on('response', vi.fn());
      handler.on('response', vi.fn());
      handler.on('error', vi.fn());
      
      expect(handler.getHandlerCount('response')).toBe(2);
      expect(handler.getHandlerCount('error')).toBe(1);
      expect(handler.getHandlerCount('nonexistent')).toBe(0);
      
      const allCounts = handler.getHandlerCount();
      expect(allCounts).toEqual({
        question: 0,
        response: 2,
        status: 0,
        error: 1
      });
    });
  });
});