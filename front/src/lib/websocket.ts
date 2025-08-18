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

  constructor(url: string) {
    this.url = url;
  }

  connect(token?: string): void {
    if (this.ws?.readyState === WebSocket.CONNECTING || this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connecting or connected');
      return;
    }

    console.log('Attempting to connect WebSocket to:', this.url);
    this.updateState({
      status: 'connecting',
      reconnectAttempts: this.reconnectAttempts,
    });

    try {
      // Add token to URL if provided
      const wsUrl = token ? `${this.url}?token=${encodeURIComponent(token)}` : this.url;
      console.log('WebSocket URL with token:', wsUrl.replace(/token=[^&]+/, 'token=***'));
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.handleError(error as Event);
    }
  }

  disconnect(): void {
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

  private handleOpen(): void {
    console.log('WebSocket connected');
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

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      // Notify listeners for this message type
      const listeners = this.listeners.get(message.type);
      if (listeners) {
        listeners.forEach(callback => callback(message));
      }

      // Notify listeners for all messages
      const allListeners = this.listeners.get('*');
      if (allListeners) {
        allListeners.forEach(callback => callback(message));
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private handleClose(event: CloseEvent): void {
    console.log('WebSocket closed:', {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean,
      url: this.url
    });
    
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    // Don't reconnect if it was a normal closure
    if (event.code === 1000) {
      this.updateState({
        status: 'disconnected',
        reconnectAttempts: this.reconnectAttempts,
      });
      return;
    }

    // Attempt reconnection with exponential backoff
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnect();
    } else {
      this.updateState({
        status: 'error',
        lastError: 'Max reconnection attempts reached',
        reconnectAttempts: this.reconnectAttempts,
      });
    }
  }

  private handleError(event: Event): void {
    console.error('WebSocket error:', {
      event,
      url: this.url,
      readyState: this.ws?.readyState,
      reconnectAttempts: this.reconnectAttempts
    });
    this.updateState({
      status: 'error',
      lastError: 'Connection error',
      reconnectAttempts: this.reconnectAttempts,
    });
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.updateState({
      status: 'connecting',
      reconnectAttempts: this.reconnectAttempts,
    });

    this.reconnectTimer = setTimeout(() => {
      this.connect();
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

  private updateState(state: WebSocketState): void {
    this.stateListeners.forEach(callback => callback(state));
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