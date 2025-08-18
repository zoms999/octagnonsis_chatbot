import { useAuth } from '@/providers/auth-provider';

export interface WebSocketState {
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastError?: string;
  reconnectAttempts: number;
}

export interface WebSocketMessage {
  type: 'question' | 'status' | 'response' | 'error';
  data: any;
  timestamp: string;
}

export interface QuestionMessage {
  type: 'question';
  data: {
    question: string;
    conversation_id?: string;
  };
}

export interface StatusMessage {
  type: 'status';
  data: {
    status: 'processing' | 'generating' | 'complete';
    progress?: number;
  };
}

export interface ResponseMessage {
  type: 'response';
  data: {
    conversation_id: string;
    response: string;
    retrieved_documents: any[];
    confidence_score: number;
    processing_time: number;
  };
}

export interface ErrorMessage {
  type: 'error';
  data: {
    message: string;
    code?: string;
  };
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private maxReconnectDelay = 30000; // Max 30 seconds
  private messageQueue: WebSocketMessage[] = [];
  private listeners: Map<string, Set<(message: WebSocketMessage) => void>> = new Map();
  private stateListeners: Set<(state: WebSocketState) => void> = new Set();
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private heartbeatInterval = 30000; // 30 seconds
  private isConnecting = false; // Prevent connection loops
  private isManuallyDisconnected = false; // Track manual disconnections
  private connectionId = 0; // Track connection attempts

  constructor(url: string) {
    this.url = url;
  }

  connect(token?: string): void {
    // Prevent connection loops - check if already connecting or connected
    if (this.isConnecting || this.ws?.readyState === WebSocket.CONNECTING || this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connecting or connected, skipping connection attempt');
      return;
    }

    // Clear any existing reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // Set connecting flag to prevent loops
    this.isConnecting = true;
    this.isManuallyDisconnected = false;
    this.connectionId++;
    const currentConnectionId = this.connectionId;

    console.log(`Attempting to connect WebSocket to: ${this.url} (connection #${currentConnectionId})`);
    this.updateState({
      status: 'connecting',
      reconnectAttempts: this.reconnectAttempts,
    });

    try {
      // Add token to URL if provided
      const wsUrl = token ? `${this.url}?token=${encodeURIComponent(token)}` : this.url;
      console.log('WebSocket URL with token:', wsUrl.replace(/token=[^&]+/, 'token=***'));
      this.ws = new WebSocket(wsUrl);

      // Bind event handlers with connection ID to prevent stale handlers
      this.ws.onopen = (event) => this.handleOpen(event, currentConnectionId);
      this.ws.onmessage = (event) => this.handleMessage(event, currentConnectionId);
      this.ws.onclose = (event) => this.handleClose(event, currentConnectionId);
      this.ws.onerror = (event) => this.handleError(event, currentConnectionId);

      // Set a connection timeout
      setTimeout(() => {
        if (this.connectionId === currentConnectionId && this.isConnecting && this.ws?.readyState === WebSocket.CONNECTING) {
          console.warn(`WebSocket connection timeout for connection #${currentConnectionId}`);
          this.ws?.close();
          this.handleConnectionTimeout(currentConnectionId);
        }
      }, 10000); // 10 second timeout

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.isConnecting = false;
      this.handleError(error as Event, currentConnectionId);
    }
  }

  disconnect(): void {
    console.log('Manually disconnecting WebSocket');
    this.isManuallyDisconnected = true;
    this.isConnecting = false;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.updateState({
      status: 'disconnected',
      reconnectAttempts: this.reconnectAttempts,
    });
  }

  send(message: WebSocketMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // Queue message for later sending
      this.messageQueue.push(message);
    }
  }

  subscribe(eventType: string, callback: (message: WebSocketMessage) => void): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);

    // Return unsubscribe function
    return () => {
      const listeners = this.listeners.get(eventType);
      if (listeners) {
        listeners.delete(callback);
        if (listeners.size === 0) {
          this.listeners.delete(eventType);
        }
      }
    };
  }

  subscribeToState(callback: (state: WebSocketState) => void): () => void {
    this.stateListeners.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.stateListeners.delete(callback);
    };
  }

  getState(): WebSocketState {
    if (!this.ws) {
      return {
        status: 'disconnected',
        reconnectAttempts: this.reconnectAttempts,
      };
    }

    const status = this.ws.readyState === WebSocket.OPEN ? 'connected' :
                   this.ws.readyState === WebSocket.CONNECTING ? 'connecting' :
                   this.ws.readyState === WebSocket.CLOSING ? 'disconnected' :
                   this.ws.readyState === WebSocket.CLOSED ? 'disconnected' : 'error';

    return {
      status,
      reconnectAttempts: this.reconnectAttempts,
    };
  }

  // Reset connection state and force reconnect
  reset(): void {
    console.log('Resetting WebSocket client state');
    this.disconnect();
    this.reconnectAttempts = 0;
    this.isConnecting = false;
    this.isManuallyDisconnected = false;
    this.connectionId++;
    this.messageQueue = [];
  }

  // Check if client is in a healthy state
  isHealthy(): boolean {
    return this.ws?.readyState === WebSocket.OPEN && !this.isConnecting;
  }

  private handleOpen(event: Event, connectionId: number): void {
    // Ignore events from old connections
    if (connectionId !== this.connectionId) {
      console.log(`Ignoring open event from old connection #${connectionId}`);
      return;
    }

    console.log(`WebSocket connected (connection #${connectionId})`);
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.reconnectDelay = 1000; // Reset delay

    this.updateState({
      status: 'connected',
      reconnectAttempts: this.reconnectAttempts,
    });

    // Send queued messages
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(message));
      }
    }

    // Start heartbeat
    this.startHeartbeat();
  }

  private handleMessage(event: MessageEvent, connectionId: number): void {
    // Ignore events from old connections
    if (connectionId !== this.connectionId) {
      console.log(`Ignoring message event from old connection #${connectionId}`);
      return;
    }

    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      // Handle pong responses for heartbeat
      if (message.type === 'pong') {
        console.log('Received pong response');
        return;
      }
      
      // Notify listeners for this message type
      const listeners = this.listeners.get(message.type);
      if (listeners) {
        listeners.forEach(callback => {
          try {
            callback(message);
          } catch (error) {
            console.error(`Error in message listener for ${message.type}:`, error);
          }
        });
      }

      // Notify listeners for all messages
      const allListeners = this.listeners.get('*');
      if (allListeners) {
        allListeners.forEach(callback => {
          try {
            callback(message);
          } catch (error) {
            console.error('Error in wildcard message listener:', error);
          }
        });
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private handleClose(event: CloseEvent, connectionId: number): void {
    // Ignore events from old connections
    if (connectionId !== this.connectionId) {
      console.log(`Ignoring close event from old connection #${connectionId}`);
      return;
    }

    console.log(`WebSocket closed (connection #${connectionId}):`, {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean,
      url: this.url,
      isManuallyDisconnected: this.isManuallyDisconnected
    });
    
    this.isConnecting = false;
    
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    // Don't reconnect if it was a manual disconnection or normal closure
    if (this.isManuallyDisconnected || event.code === 1000) {
      this.updateState({
        status: 'disconnected',
        reconnectAttempts: this.reconnectAttempts,
      });
      return;
    }

    // Handle different close codes with appropriate responses
    const shouldReconnect = this.shouldAttemptReconnect(event.code);
    
    if (shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnect();
    } else {
      const errorMessage = this.getCloseErrorMessage(event.code);
      this.updateState({
        status: 'error',
        lastError: errorMessage,
        reconnectAttempts: this.reconnectAttempts,
      });
    }
  }

  private handleError(event: Event, connectionId: number): void {
    // Ignore events from old connections
    if (connectionId !== this.connectionId) {
      console.log(`Ignoring error event from old connection #${connectionId}`);
      return;
    }

    console.error(`WebSocket error (connection #${connectionId}):`, {
      event,
      url: this.url,
      readyState: this.ws?.readyState,
      reconnectAttempts: this.reconnectAttempts,
      isConnecting: this.isConnecting
    });
    
    this.isConnecting = false;
    
    this.updateState({
      status: 'error',
      lastError: 'Connection error',
      reconnectAttempts: this.reconnectAttempts,
    });
  }

  private scheduleReconnect(): void {
    // Prevent multiple reconnect timers and manual disconnections
    if (this.reconnectTimer || this.isManuallyDisconnected || this.isConnecting) {
      console.log('Reconnect already scheduled or manually disconnected, skipping');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );

    console.log(`Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.updateState({
      status: 'connecting',
      reconnectAttempts: this.reconnectAttempts,
    });

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null; // Clear timer reference
      
      // Double-check we should still reconnect
      if (!this.isManuallyDisconnected && this.reconnectAttempts <= this.maxReconnectAttempts) {
        console.log(`Executing reconnect attempt ${this.reconnectAttempts}`);
        this.connect();
      } else {
        console.log('Skipping reconnect - manually disconnected or max attempts reached');
      }
    }, delay);
  }

  private startHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }

    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({
          type: 'ping' as any,
          data: {},
          timestamp: new Date().toISOString(),
        });
      }
    }, this.heartbeatInterval);
  }

  private handleConnectionTimeout(connectionId: number): void {
    if (connectionId !== this.connectionId) {
      return;
    }

    console.error(`WebSocket connection timeout (connection #${connectionId})`);
    this.isConnecting = false;
    
    this.updateState({
      status: 'error',
      lastError: 'Connection timeout',
      reconnectAttempts: this.reconnectAttempts,
    });

    // Schedule reconnect if not manually disconnected
    if (!this.isManuallyDisconnected && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnect();
    }
  }

  private shouldAttemptReconnect(closeCode: number): boolean {
    // Don't reconnect for certain close codes
    const noReconnectCodes = [
      1000, // Normal closure
      1001, // Going away
      1005, // No status received
      4000, // Authentication failed
      4001, // Unauthorized
      4003, // Forbidden
    ];

    return !noReconnectCodes.includes(closeCode);
  }

  private getCloseErrorMessage(closeCode: number): string {
    switch (closeCode) {
      case 1006:
        return 'Connection lost unexpectedly';
      case 1011:
        return 'Server error occurred';
      case 1012:
        return 'Server is restarting';
      case 1013:
        return 'Server is temporarily unavailable';
      case 4000:
        return 'Authentication failed';
      case 4001:
        return 'Unauthorized access';
      case 4003:
        return 'Access forbidden';
      default:
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          return 'Max reconnection attempts reached';
        }
        return 'Connection error';
    }
  }

  private updateState(state: WebSocketState): void {
    this.stateListeners.forEach(callback => {
      try {
        callback(state);
      } catch (error) {
        console.error('Error in state listener:', error);
      }
    });
  }
}

// Global WebSocket instance
let globalWebSocketClient: WebSocketClient | null = null;

export function getWebSocketClient(userId?: string): WebSocketClient {
  if (!globalWebSocketClient && userId) {
    const wsBase = process.env.NEXT_PUBLIC_WS_BASE || 'ws://localhost:8000';
    const wsUrl = `${wsBase}/api/chat/ws/${userId}`;
    console.log('Creating WebSocket client with URL:', wsUrl);
    globalWebSocketClient = new WebSocketClient(wsUrl);
  }
  
  if (!globalWebSocketClient) {
    throw new Error('WebSocket client not initialized. User ID required.');
  }
  
  return globalWebSocketClient;
}

export function resetWebSocketClient(): void {
  if (globalWebSocketClient) {
    globalWebSocketClient.disconnect();
    globalWebSocketClient = null;
  }
}

// Add method to force reconnect
export function forceReconnectWebSocket(userId?: string): void {
  if (globalWebSocketClient) {
    globalWebSocketClient.disconnect();
    // Wait a bit before reconnecting to ensure clean state
    setTimeout(() => {
      if (userId) {
        const client = getWebSocketClient(userId);
        client.connect();
      }
    }, 1000);
  }
}