import { WebSocketMessage, ChatResponse, DocumentReference } from './types';

// Message validation schemas
export interface MessageValidationResult {
  isValid: boolean;
  errors: string[];
}

// Rate limiting configuration
export interface RateLimitConfig {
  maxMessages: number;
  windowMs: number;
}

export class RateLimiter {
  private messageTimestamps: number[] = [];
  private config: RateLimitConfig;

  constructor(config: RateLimitConfig = { maxMessages: 10, windowMs: 60000 }) {
    this.config = config;
  }

  canSendMessage(): boolean {
    const now = Date.now();
    const windowStart = now - this.config.windowMs;

    // Remove old timestamps outside the window
    this.messageTimestamps = this.messageTimestamps.filter(
      timestamp => timestamp > windowStart
    );

    return this.messageTimestamps.length < this.config.maxMessages;
  }

  recordMessage(): void {
    this.messageTimestamps.push(Date.now());
  }

  getTimeUntilNextMessage(): number {
    if (this.canSendMessage()) return 0;

    const oldestTimestamp = Math.min(...this.messageTimestamps);
    const timeUntilExpiry = (oldestTimestamp + this.config.windowMs) - Date.now();
    return Math.max(0, timeUntilExpiry);
  }

  getRemainingMessages(): number {
    const now = Date.now();
    const windowStart = now - this.config.windowMs;
    const recentMessages = this.messageTimestamps.filter(
      timestamp => timestamp > windowStart
    );
    return Math.max(0, this.config.maxMessages - recentMessages.length);
  }
}

// Message validators
export class MessageValidator {
  static validateQuestionMessage(message: any): MessageValidationResult {
    const errors: string[] = [];

    if (!message.data) {
      errors.push('Message data is required');
      return { isValid: false, errors };
    }

    if (!message.data.question || typeof message.data.question !== 'string') {
      errors.push('Question is required and must be a string');
    }

    if (message.data.question && message.data.question.trim().length === 0) {
      errors.push('Question cannot be empty');
    }

    if (message.data.question && message.data.question.length > 1000) {
      errors.push('Question must be less than 1000 characters');
    }

    if (message.data.conversation_id && typeof message.data.conversation_id !== 'string') {
      errors.push('Conversation ID must be a string');
    }

    return { isValid: errors.length === 0, errors };
  }

  static validateResponseMessage(message: any): MessageValidationResult {
    const errors: string[] = [];

    if (!message.data) {
      errors.push('Message data is required');
      return { isValid: false, errors };
    }

    const requiredFields = ['conversation_id', 'response'];
    for (const field of requiredFields) {
      if (!message.data[field]) {
        errors.push(`${field} is required`);
      }
    }

    if (message.data.confidence_score !== undefined) {
      const score = message.data.confidence_score;
      if (typeof score !== 'number' || score < 0 || score > 1) {
        errors.push('Confidence score must be a number between 0 and 1');
      }
    }

    if (message.data.processing_time !== undefined) {
      const time = message.data.processing_time;
      if (typeof time !== 'number' || time < 0) {
        errors.push('Processing time must be a non-negative number');
      }
    }

    return { isValid: errors.length === 0, errors };
  }

  static validateStatusMessage(message: any): MessageValidationResult {
    const errors: string[] = [];

    if (!message.data) {
      errors.push('Message data is required');
      return { isValid: false, errors };
    }

    if (!message.data.status) {
      errors.push('Status is required');
    } else {
      const validStatuses = ['processing', 'generating', 'complete'];
      if (!validStatuses.includes(message.data.status)) {
        errors.push(`Status must be one of: ${validStatuses.join(', ')}`);
      }
    }

    if (message.data.progress !== undefined) {
      const progress = message.data.progress;
      if (typeof progress !== 'number' || progress < 0 || progress > 100) {
        errors.push('Progress must be a number between 0 and 100');
      }
    }

    return { isValid: errors.length === 0, errors };
  }

  static validateErrorMessage(message: any): MessageValidationResult {
    const errors: string[] = [];

    if (!message.data) {
      errors.push('Message data is required');
      return { isValid: false, errors };
    }

    if (!message.data.message || typeof message.data.message !== 'string') {
      errors.push('Error message is required and must be a string');
    }

    return { isValid: errors.length === 0, errors };
  }

  static validateMessage(message: WebSocketMessage): MessageValidationResult {
    // Basic structure validation
    if (!message.type || !message.timestamp) {
      return {
        isValid: false,
        errors: ['Message type and timestamp are required']
      };
    }

    // Type-specific validation
    switch (message.type) {
      case 'question':
        return this.validateQuestionMessage(message);
      case 'response':
        return this.validateResponseMessage(message);
      case 'status':
        return this.validateStatusMessage(message);
      case 'error':
        return this.validateErrorMessage(message);
      default:
        return {
          isValid: false,
          errors: [`Unknown message type: ${message.type}`]
        };
    }
  }
}

// Message handlers
export type MessageHandler<T = any> = (message: WebSocketMessage) => void;

export interface MessageHandlerRegistry {
  question: MessageHandler[];
  response: MessageHandler[];
  status: MessageHandler[];
  error: MessageHandler[];
  [key: string]: MessageHandler[];
}

export class WebSocketMessageHandler {
  private handlers: MessageHandlerRegistry = {
    question: [],
    response: [],
    status: [],
    error: [],
  };

  private rateLimiter: RateLimiter;
  private onRateLimitExceeded?: (timeUntilNext: number) => void;
  private sentMessageIds: Set<string> = new Set();
  private messageIdCleanupInterval: NodeJS.Timeout | null = null;

  constructor(
    rateLimitConfig?: RateLimitConfig,
    onRateLimitExceeded?: (timeUntilNext: number) => void
  ) {
    this.rateLimiter = new RateLimiter(rateLimitConfig);
    this.onRateLimitExceeded = onRateLimitExceeded;
    
    // Clean up old message IDs every 5 minutes
    this.messageIdCleanupInterval = setInterval(() => {
      this.sentMessageIds.clear();
    }, 5 * 60 * 1000);
  }

  // Register message handlers
  on<T = any>(eventType: string, handler: MessageHandler<T>): () => void {
    if (!this.handlers[eventType]) {
      this.handlers[eventType] = [];
    }
    
    this.handlers[eventType].push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.handlers[eventType];
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  // Handle incoming messages
  handleMessage(message: WebSocketMessage): void {
    // Validate message
    const validation = MessageValidator.validateMessage(message);
    if (!validation.isValid) {
      console.error('Invalid WebSocket message:', validation.errors);
      this.emitError({
        message: `Invalid message: ${validation.errors.join(', ')}`,
        code: 'VALIDATION_ERROR'
      });
      return;
    }

    // Emit to specific handlers
    const handlers = this.handlers[message.type] || [];
    handlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error(`Error in message handler for ${message.type}:`, error);
      }
    });

    // Emit to wildcard handlers
    const wildcardHandlers = this.handlers['*'] || [];
    wildcardHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('Error in wildcard message handler:', error);
      }
    });
  }

  // Send message with rate limiting and deduplication
  sendMessage(
    message: WebSocketMessage,
    sendFunction: (message: WebSocketMessage) => void
  ): boolean {
    // Create message ID for deduplication (for question messages)
    if (message.type === 'question') {
      const messageId = `${message.data.question}-${message.data.conversation_id || 'new'}`;
      
      // Check if we've already sent this message recently
      if (this.sentMessageIds.has(messageId)) {
        console.log('Duplicate message detected, skipping:', messageId);
        return false;
      }
      
      // Mark message as sent
      this.sentMessageIds.add(messageId);
    }

    // Check rate limit for outgoing messages
    if (message.type === 'question' && !this.rateLimiter.canSendMessage()) {
      const timeUntilNext = this.rateLimiter.getTimeUntilNextMessage();
      this.onRateLimitExceeded?.(timeUntilNext);
      return false;
    }

    // Validate message before sending
    const validation = MessageValidator.validateMessage(message);
    if (!validation.isValid) {
      this.emitError({
        message: `Cannot send invalid message: ${validation.errors.join(', ')}`,
        code: 'VALIDATION_ERROR'
      });
      return false;
    }

    try {
      sendFunction(message);
      
      // Record message for rate limiting
      if (message.type === 'question') {
        this.rateLimiter.recordMessage();
      }
      
      return true;
    } catch (error) {
      this.emitError({
        message: `Failed to send message: ${error}`,
        code: 'SEND_ERROR'
      });
      return false;
    }
  }

  // Get rate limit status
  getRateLimitStatus() {
    return {
      canSendMessage: this.rateLimiter.canSendMessage(),
      remainingMessages: this.rateLimiter.getRemainingMessages(),
      timeUntilNextMessage: this.rateLimiter.getTimeUntilNextMessage(),
    };
  }

  // Emit error message
  private emitError(errorData: { message: string; code?: string }): void {
    const errorMessage: WebSocketMessage = {
      type: 'error',
      data: errorData,
      timestamp: new Date().toISOString(),
    };

    const errorHandlers = this.handlers.error || [];
    errorHandlers.forEach(handler => {
      try {
        handler(errorMessage);
      } catch (error) {
        console.error('Error in error message handler:', error);
      }
    });
  }

  // Clear all handlers
  clearHandlers(): void {
    Object.keys(this.handlers).forEach(key => {
      this.handlers[key] = [];
    });
    
    // Clear message ID tracking
    this.sentMessageIds.clear();
    
    // Clear cleanup interval
    if (this.messageIdCleanupInterval) {
      clearInterval(this.messageIdCleanupInterval);
      this.messageIdCleanupInterval = null;
    }
  }

  // Get handler count for debugging
  getHandlerCount(eventType?: string): number | Record<string, number> {
    if (eventType) {
      return this.handlers[eventType]?.length || 0;
    }

    const counts: Record<string, number> = {};
    Object.keys(this.handlers).forEach(key => {
      counts[key] = this.handlers[key].length;
    });
    return counts;
  }
}