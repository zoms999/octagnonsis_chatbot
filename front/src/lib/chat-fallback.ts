import { ApiClient } from './api';
import { ChatResponse, WebSocketMessage } from './types';

export interface ChatFallbackConfig {
  maxRetries: number;
  retryDelay: number;
  timeout: number;
}

export interface ChatFallbackResult {
  success: boolean;
  data?: ChatResponse;
  error?: string;
  usedFallback: boolean;
}

export class ChatFallbackHandler {
  private config: ChatFallbackConfig;
  private isWebSocketAvailable: boolean = true;
  private fallbackActive: boolean = false;

  constructor(config: ChatFallbackConfig = {
    maxRetries: 3,
    retryDelay: 1000,
    timeout: 30000
  }) {
    this.config = config;
  }

  // Set WebSocket availability status
  setWebSocketAvailable(available: boolean): void {
    this.isWebSocketAvailable = available;
    if (available) {
      this.fallbackActive = false;
    }
  }

  // Check if fallback should be used
  shouldUseFallback(): boolean {
    return !this.isWebSocketAvailable || this.fallbackActive;
  }

  // Send question via HTTP fallback
  async sendQuestionHTTP(
    question: string,
    conversationId?: string,
    userId?: string
  ): Promise<ChatFallbackResult> {
    console.log('ChatFallbackHandler.sendQuestionHTTP called:', {
      question: question.substring(0, 50) + '...',
      conversationId,
      userId
    });

    if (!userId) {
      console.error('User ID is required for HTTP fallback');
      return {
        success: false,
        error: 'User ID is required for HTTP fallback',
        usedFallback: true
      };
    }

    let lastError: string = '';
    
    for (let attempt = 0; attempt < this.config.maxRetries; attempt++) {
      try {
        console.log(`HTTP fallback attempt ${attempt + 1}/${this.config.maxRetries}`);
        const response = await this.makeHTTPRequest(question, conversationId, userId);
        console.log('HTTP request successful:', response);
        
        return {
          success: true,
          data: response,
          usedFallback: true
        };
      } catch (error: any) {
        lastError = error.message || 'HTTP request failed';
        console.error(`HTTP fallback attempt ${attempt + 1} failed:`, error);
        
        // Don't retry on certain errors
        if (error.status === 401 || error.status === 403) {
          console.log('Not retrying due to auth error');
          break;
        }

        // Wait before retry (except on last attempt)
        if (attempt < this.config.maxRetries - 1) {
          const delay = this.config.retryDelay * (attempt + 1);
          console.log(`Waiting ${delay}ms before retry...`);
          await this.delay(delay);
        }
      }
    }

    console.error('All HTTP fallback attempts failed:', lastError);
    return {
      success: false,
      error: lastError,
      usedFallback: true
    };
  }

  // Make HTTP request with timeout
  private async makeHTTPRequest(
    question: string,
    conversationId?: string,
    userId?: string
  ): Promise<ChatResponse> {
    console.log('Making HTTP request to API:', {
      question: question.substring(0, 50) + '...',
      conversationId,
      timeout: this.config.timeout
    });

    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      console.log('HTTP request timeout reached');
      controller.abort();
    }, this.config.timeout);

    try {
      // Use the ApiClient.sendQuestion method which handles the correct endpoint
      console.log('Calling ApiClient.sendQuestion with userId:', userId);
      const response = await ApiClient.sendQuestion(question, conversationId, userId);
      console.log('ApiClient.sendQuestion response:', response);
      return response;
    } catch (error) {
      console.error('HTTP request failed:', error);
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // Utility delay function
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Activate fallback mode
  activateFallback(): void {
    this.fallbackActive = true;
  }

  // Deactivate fallback mode
  deactivateFallback(): void {
    this.fallbackActive = false;
  }

  // Get fallback status
  getStatus() {
    return {
      isWebSocketAvailable: this.isWebSocketAvailable,
      fallbackActive: this.fallbackActive,
      shouldUseFallback: this.shouldUseFallback()
    };
  }
}

// Enhanced WebSocket message handler with HTTP fallback
export class EnhancedChatHandler {
  private fallbackHandler: ChatFallbackHandler;
  private onMessage?: (message: WebSocketMessage) => void;
  private onError?: (error: string) => void;
  private onFallbackUsed?: (reason: string) => void;

  constructor(
    fallbackConfig?: ChatFallbackConfig,
    callbacks?: {
      onMessage?: (message: WebSocketMessage) => void;
      onError?: (error: string) => void;
      onFallbackUsed?: (reason: string) => void;
    }
  ) {
    this.fallbackHandler = new ChatFallbackHandler(fallbackConfig);
    this.onMessage = callbacks?.onMessage;
    this.onError = callbacks?.onError;
    this.onFallbackUsed = callbacks?.onFallbackUsed;
    
    console.log('EnhancedChatHandler constructor:', {
      hasOnMessage: !!this.onMessage,
      hasOnError: !!this.onError,
      hasOnFallbackUsed: !!this.onFallbackUsed
    });
  }

  // Send question with automatic fallback
  async sendQuestion(
    question: string,
    conversationId?: string,
    userId?: string,
    webSocketSend?: (message: WebSocketMessage) => void
  ): Promise<void> {
    console.log('EnhancedChatHandler.sendQuestion called:', {
      question: question.substring(0, 50) + '...',
      conversationId,
      userId,
      hasWebSocketSend: !!webSocketSend,
      shouldUseFallback: this.fallbackHandler.shouldUseFallback(),
      fallbackStatus: this.fallbackHandler.getStatus()
    });

    // Check if WebSocket is actually connected
    if (webSocketSend) {
      console.log('WebSocket send function is available, checking connection status...');
    }

    // Try WebSocket first if available and not forced to use fallback
    if (!this.fallbackHandler.shouldUseFallback() && webSocketSend) {
      try {
        console.log('Attempting WebSocket send...');
        const message: WebSocketMessage = {
          type: 'question',
          data: {
            question,
            conversation_id: conversationId
          },
          timestamp: new Date().toISOString()
        };

        webSocketSend(message);
        console.log('WebSocket message sent successfully');
        return;
      } catch (error) {
        console.warn('WebSocket send failed, falling back to HTTP:', error);
        this.fallbackHandler.activateFallback();
        this.onFallbackUsed?.('WebSocket send failed');
      }
    }

    // Use HTTP fallback
    console.log('Using HTTP fallback...');
    const result = await this.fallbackHandler.sendQuestionHTTP(
      question,
      conversationId,
      userId
    );

    console.log('HTTP fallback result:', result);

    if (result.success && result.data) {
      // Convert HTTP response to WebSocket message format
      const responseMessage: WebSocketMessage = {
        type: 'response',
        data: result.data,
        timestamp: new Date().toISOString()
      };

      console.log('Calling onMessage with response:', responseMessage);
      console.log('this.onMessage exists:', !!this.onMessage);
      if (this.onMessage) {
        console.log('Actually calling this.onMessage...');
        this.onMessage(responseMessage);
        console.log('this.onMessage call completed');
      } else {
        console.error('this.onMessage is undefined!');
      }
      
      if (result.usedFallback) {
        this.onFallbackUsed?.('WebSocket unavailable');
      }
    } else {
      console.error('HTTP fallback failed:', result.error);
      this.onError?.(result.error || 'Failed to send question');
    }
  }

  // Handle WebSocket connection status changes
  onWebSocketStatusChange(connected: boolean): void {
    this.fallbackHandler.setWebSocketAvailable(connected);
    
    if (connected) {
      console.log('WebSocket reconnected, disabling fallback mode');
    } else {
      console.log('WebSocket disconnected, fallback mode available');
    }
  }

  // Get current status
  getStatus() {
    return this.fallbackHandler.getStatus();
  }

  // Force fallback mode
  forceFallback(): void {
    this.fallbackHandler.activateFallback();
    this.onFallbackUsed?.('Manually activated');
  }

  // Disable fallback mode
  disableFallback(): void {
    this.fallbackHandler.deactivateFallback();
  }
}