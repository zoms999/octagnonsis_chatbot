import { ApiClient } from './api';
import { ChatResponse, ChatMessage } from './types';
import { extractUserId } from './user-utils';
import { ChatErrorHandler, ErrorContext } from './chat-error-handler';

export interface SimpleChatConfig {
  enableDebugLogging?: boolean;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
}

export interface SimpleChatResult {
  success: boolean;
  data?: ChatResponse;
  error?: string;
}

export interface SimpleChatCallbacks {
  onMessage?: (message: ChatMessage) => void;
  onError?: (error: string, chatError?: any) => void;
  onProcessingStart?: () => void;
  onProcessingEnd?: () => void;
}

/**
 * Improved simplified chat handler with better response processing and error handling
 */
export class SimpleChatHandler {
  private config: SimpleChatConfig;
  private callbacks: SimpleChatCallbacks;
  private isProcessing: boolean = false;
  private requestCounter: number = 0;

  constructor(
    config: SimpleChatConfig = {},
    callbacks: SimpleChatCallbacks = {}
  ) {
    this.config = {
      enableDebugLogging: true,
      timeout: 30000, // 30 seconds
      maxRetries: 2,
      retryDelay: 1000,
      ...config
    };
    this.callbacks = callbacks;
  }

  /**
   * Send a question directly via HTTP API with improved response handling
   */
  async sendQuestion(
    question: string,
    conversationId?: string,
    userId?: string
  ): Promise<SimpleChatResult> {
    if (this.isProcessing) {
      const error = 'Already processing a message. Please wait.';
      this.log('Blocked duplicate request:', error);
      return { success: false, error };
    }

    if (!question.trim()) {
      const error = 'Question cannot be empty';
      this.log('Invalid question:', error);
      return { success: false, error };
    }

    if (!userId) {
      const error = 'User ID is required for chat requests';
      this.log('Missing user ID:', error);
      return { success: false, error };
    }

    const requestId = ++this.requestCounter;
    this.log(`[Request ${requestId}] Sending question via HTTP:`, {
      question: question.substring(0, 50) + '...',
      conversationId,
      userId,
      questionLength: question.length
    });

    this.isProcessing = true;
    this.callbacks.onProcessingStart?.();

    try {
      const result = await this.makeHttpRequest(question, conversationId, userId, requestId);
      
      if (result.success && result.data) {
        // Convert API response to chat message format with improved handling
        const responseMessage: ChatMessage = this.createChatMessageFromResponse(result.data, requestId);

        this.log(`[Request ${requestId}] HTTP request successful, calling onMessage callback with message:`, {
          id: responseMessage.id,
          contentLength: responseMessage.content?.length,
          conversationId: responseMessage.conversation_id,
          retrievedDocsCount: responseMessage.retrieved_documents?.length,
          processingTime: responseMessage.processing_time
        });
        
        this.callbacks.onMessage?.(responseMessage);
      } else {
        this.log(`[Request ${requestId}] HTTP request completed but no valid data received:`, result);
        if (result.error) {
          this.callbacks.onError?.(result.error);
        }
      }

      return result;
    } catch (error: any) {
      // Process error through enhanced error handler
      const context: ErrorContext = {
        userId,
        conversationId,
        question: question.substring(0, 100),
        endpoint: '/api/chat/question',
        requestPayload: { question, conversation_id: conversationId, user_id: userId }
      };
      
      const chatError = ChatErrorHandler.processError(error, context);
      
      this.log(`[Request ${requestId}] HTTP request failed:`, {
        type: chatError.type,
        message: chatError.message,
        recoverable: chatError.recoverable,
        userMessage: chatError.userMessage
      });
      
      this.callbacks.onError?.(chatError.userMessage, chatError);
      return { success: false, error: chatError.userMessage };
    } finally {
      this.isProcessing = false;
      this.callbacks.onProcessingEnd?.();
    }
  }

  /**
   * Create a ChatMessage from API response with proper validation and defaults
   */
  private createChatMessageFromResponse(data: ChatResponse, requestId: number): ChatMessage {
    // Ensure we have valid content
    if (!data.response || typeof data.response !== 'string') {
      throw new Error('Invalid response content received from API');
    }

    // Create unique message ID
    const messageId = `response-${requestId}-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    // Parse timestamp or use current time
    let timestamp: Date;
    try {
      timestamp = data.timestamp ? new Date(data.timestamp) : new Date();
      // Validate timestamp
      if (isNaN(timestamp.getTime())) {
        timestamp = new Date();
      }
    } catch {
      timestamp = new Date();
    }

    // Ensure retrieved_documents is an array
    const retrievedDocuments = Array.isArray(data.retrieved_documents) 
      ? data.retrieved_documents 
      : [];

    return {
      id: messageId,
      type: 'assistant',
      content: data.response,
      timestamp,
      conversation_id: data.conversation_id,
      confidence_score: typeof data.confidence_score === 'number' ? data.confidence_score : undefined,
      processing_time: typeof data.processing_time === 'number' ? data.processing_time : undefined,
      retrieved_documents: retrievedDocuments,
    };
  }

  /**
   * Make HTTP request with improved retry logic and error handling
   */
  private async makeHttpRequest(
    question: string,
    conversationId?: string,
    userId?: string,
    requestId?: number
  ): Promise<SimpleChatResult> {
    let lastError: string = '';
    const maxRetries = this.config.maxRetries || 2;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        this.log(`[Request ${requestId}] HTTP request attempt ${attempt + 1}/${maxRetries}`);
        
        // Use ApiClient.sendQuestion which handles the correct endpoint and authentication
        const response = await ApiClient.sendQuestion(question, conversationId, userId);
        
        // Validate response structure
        if (!response || typeof response !== 'object') {
          throw new Error('Invalid response format received from API');
        }

        if (!response.response) {
          throw new Error('No response content received from API');
        }
        
        this.log(`[Request ${requestId}] HTTP request successful:`, {
          conversationId: response.conversation_id,
          responseLength: response.response?.length,
          confidenceScore: response.confidence_score,
          processingTime: response.processing_time,
          retrievedDocsCount: response.retrieved_documents?.length
        });
        
        return {
          success: true,
          data: response
        };
      } catch (error: any) {
        lastError = error.message || 'HTTP request failed';
        // Process error for better classification
        const context: ErrorContext = {
          userId,
          conversationId,
          question: question.substring(0, 100),
          endpoint: '/api/chat/question'
        };
        
        const chatError = ChatErrorHandler.processError(error, context);
        lastError = chatError.userMessage;
        
        this.log(`[Request ${requestId}] HTTP request attempt ${attempt + 1} failed:`, {
          type: chatError.type,
          message: chatError.message,
          recoverable: chatError.recoverable,
          status: error.status
        });
        
        // Don't retry on certain errors
        if (error.status === 401 || error.status === 403 || error.status === 400) {
          this.log(`[Request ${requestId}] Not retrying due to client error:`, error.status);
          break;
        }

        // Wait before retry (except on last attempt)
        if (attempt < maxRetries - 1) {
          const delay = (this.config.retryDelay || 1000) * (attempt + 1);
          this.log(`[Request ${requestId}] Waiting ${delay}ms before retry...`);
          await this.delay(delay);
        }
      }
    }

    this.log(`[Request ${requestId}] All HTTP request attempts failed:`, lastError);
    return {
      success: false,
      error: lastError
    };
  }

  /**
   * Check if currently processing a message
   */
  isCurrentlyProcessing(): boolean {
    return this.isProcessing;
  }

  /**
   * Get current configuration
   */
  getConfig(): SimpleChatConfig {
    return { ...this.config };
  }

  /**
   * Update callbacks
   */
  updateCallbacks(callbacks: Partial<SimpleChatCallbacks>): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /**
   * Utility delay function
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Debug logging utility with request tracking
   */
  private log(message: string, data?: any): void {
    if (this.config.enableDebugLogging) {
      if (data) {
        console.log(`[SimpleChatHandler] ${message}`, data);
      } else {
        console.log(`[SimpleChatHandler] ${message}`);
      }
    }
  }
}

/**
 * Create a simple chat handler instance with default configuration
 */
export function createSimpleChatHandler(
  callbacks: SimpleChatCallbacks = {},
  config: SimpleChatConfig = {}
): SimpleChatHandler {
  return new SimpleChatHandler(config, callbacks);
}

/**
 * Utility function to send a question using the simple chat handler
 * This is a convenience function for one-off requests
 */
export async function sendQuestionSimple(
  question: string,
  user: any,
  conversationId?: string,
  config: SimpleChatConfig = {}
): Promise<SimpleChatResult> {
  const userId = extractUserId(user);
  if (!userId) {
    return {
      success: false,
      error: 'User ID could not be extracted from user object'
    };
  }

  const handler = new SimpleChatHandler(config);
  return handler.sendQuestion(question, conversationId, userId);
}