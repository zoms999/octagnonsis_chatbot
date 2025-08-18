import { ApiClient } from './api';
import { ChatResponse, ChatMessage } from './types';
import { extractUserId } from './user-utils';

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
  onError?: (error: string) => void;
  onProcessingStart?: () => void;
  onProcessingEnd?: () => void;
}

/**
 * Simplified chat handler that bypasses WebSocket complexity and uses direct HTTP calls
 * This is a temporary solution to fix the chat integration issues
 */
export class SimpleChatHandler {
  private config: SimpleChatConfig;
  private callbacks: SimpleChatCallbacks;
  private isProcessing: boolean = false;

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
   * Send a question directly via HTTP API
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

    this.log('Sending question via HTTP:', {
      question: question.substring(0, 50) + '...',
      conversationId,
      userId,
      questionLength: question.length
    });

    this.isProcessing = true;
    this.callbacks.onProcessingStart?.();

    try {
      const result = await this.makeHttpRequest(question, conversationId, userId);
      
      if (result.success && result.data) {
        // Convert API response to chat message format
        const responseMessage: ChatMessage = {
          id: `response-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'assistant',
          content: result.data.response,
          timestamp: new Date(),
          conversation_id: result.data.conversation_id,
          confidence_score: result.data.confidence_score,
          processing_time: result.data.processing_time,
          retrieved_documents: result.data.retrieved_documents,
        };

        this.log('HTTP request successful, calling onMessage callback');
        this.callbacks.onMessage?.(responseMessage);
      }

      return result;
    } catch (error: any) {
      const errorMessage = error.message || 'Failed to send question';
      this.log('HTTP request failed:', errorMessage);
      this.callbacks.onError?.(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      this.isProcessing = false;
      this.callbacks.onProcessingEnd?.();
    }
  }

  /**
   * Make HTTP request with retry logic
   */
  private async makeHttpRequest(
    question: string,
    conversationId?: string,
    userId?: string
  ): Promise<SimpleChatResult> {
    let lastError: string = '';
    
    for (let attempt = 0; attempt < (this.config.maxRetries || 2); attempt++) {
      try {
        this.log(`HTTP request attempt ${attempt + 1}/${this.config.maxRetries}`);
        
        // Use ApiClient.sendQuestion which handles the correct endpoint and authentication
        const response = await ApiClient.sendQuestion(question, conversationId, userId);
        
        this.log('HTTP request successful:', {
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
        this.log(`HTTP request attempt ${attempt + 1} failed:`, error);
        
        // Don't retry on certain errors
        if (error.status === 401 || error.status === 403 || error.status === 400) {
          this.log('Not retrying due to client error:', error.status);
          break;
        }

        // Wait before retry (except on last attempt)
        if (attempt < (this.config.maxRetries || 2) - 1) {
          const delay = (this.config.retryDelay || 1000) * (attempt + 1);
          this.log(`Waiting ${delay}ms before retry...`);
          await this.delay(delay);
        }
      }
    }

    this.log('All HTTP request attempts failed:', lastError);
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
   * Debug logging utility
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