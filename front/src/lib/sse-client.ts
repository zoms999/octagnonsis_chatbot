/**
 * Server-Sent Events (SSE) client for real-time ETL job progress monitoring
 */

import React from 'react';
import { ETLJob } from './types';

export interface SSEProgressData {
  job_id: string;
  progress: number;
  current_step: string;
  estimated_completion_time?: string;
  status: ETLJob['status'];
  error_message?: string;
}

export interface SSEConnectionState {
  isConnected: boolean;
  reconnectAttempts: number;
  lastError?: string;
}

export interface SSEClientOptions {
  onProgress?: (data: SSEProgressData) => void;
  onError?: (error: Event) => void;
  onConnectionChange?: (state: SSEConnectionState) => void;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
}

export class SSEClient {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts: number;
  private reconnectDelay: number;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private isManuallyDisconnected = false;

  constructor(
    private jobId: string,
    private options: SSEClientOptions = {}
  ) {
    this.maxReconnectAttempts = options.maxReconnectAttempts || 5;
    this.reconnectDelay = options.reconnectDelay || 1000;
  }

  /**
   * Connect to the SSE endpoint for job progress updates
   */
  connect(): void {
    if (this.eventSource) {
      this.disconnect();
    }

    this.isManuallyDisconnected = false;
    
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
      const url = `${baseUrl}/api/etl/jobs/${this.jobId}/progress`;
      
      // Include authentication token if available
      const token = this.getAuthToken();
      const urlWithAuth = token ? `${url}?token=${encodeURIComponent(token)}` : url;
      
      this.eventSource = new EventSource(urlWithAuth);
      
      this.eventSource.onopen = () => {
        this.reconnectAttempts = 0;
        this.updateConnectionState({
          isConnected: true,
          reconnectAttempts: this.reconnectAttempts,
        });
      };

      this.eventSource.onmessage = (event) => {
        try {
          const data: SSEProgressData = JSON.parse(event.data);
          this.options.onProgress?.(data);
        } catch (error) {
          console.error('Failed to parse SSE message:', error);
        }
      };

      this.eventSource.onerror = (event) => {
        this.updateConnectionState({
          isConnected: false,
          reconnectAttempts: this.reconnectAttempts,
          lastError: 'Connection error',
        });

        this.options.onError?.(event);
        
        // Attempt reconnection if not manually disconnected
        if (!this.isManuallyDisconnected && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };

    } catch (error) {
      console.error('Failed to create SSE connection:', error);
      this.updateConnectionState({
        isConnected: false,
        reconnectAttempts: this.reconnectAttempts,
        lastError: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }

  /**
   * Disconnect from the SSE endpoint
   */
  disconnect(): void {
    this.isManuallyDisconnected = true;
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    this.updateConnectionState({
      isConnected: false,
      reconnectAttempts: this.reconnectAttempts,
    });
  }

  /**
   * Get the current connection state
   */
  getConnectionState(): SSEConnectionState {
    return {
      isConnected: this.eventSource?.readyState === EventSource.OPEN,
      reconnectAttempts: this.reconnectAttempts,
    };
  }

  /**
   * Schedule a reconnection attempt with exponential backoff
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    this.reconnectTimeout = setTimeout(() => {
      if (!this.isManuallyDisconnected) {
        console.log(`Attempting SSE reconnection (attempt ${this.reconnectAttempts})`);
        this.connect();
      }
    }, delay);
  }

  /**
   * Update connection state and notify listeners
   */
  private updateConnectionState(state: SSEConnectionState): void {
    this.options.onConnectionChange?.(state);
  }

  /**
   * Get authentication token from storage
   */
  private getAuthToken(): string | null {
    // Try to get token from various storage methods
    if (typeof window !== 'undefined') {
      // Check localStorage first (fallback)
      const token = localStorage.getItem('auth_token');
      if (token) return token;

      // Check if token is available in a global context (set by auth provider)
      const globalToken = (window as any).__auth_token__;
      if (globalToken) return globalToken;
    }
    
    return null;
  }
}

/**
 * Hook for managing SSE connections in React components
 */
export function useSSEClient(
  jobId: string | null,
  options: SSEClientOptions = {}
): {
  client: SSEClient | null;
  connectionState: SSEConnectionState;
  connect: () => void;
  disconnect: () => void;
} {
  const [client, setClient] = React.useState<SSEClient | null>(null);
  const [connectionState, setConnectionState] = React.useState<SSEConnectionState>({
    isConnected: false,
    reconnectAttempts: 0,
  });

  React.useEffect(() => {
    if (!jobId) {
      setClient(null);
      return;
    }

    const sseClient = new SSEClient(jobId, {
      ...options,
      onConnectionChange: (state) => {
        setConnectionState(state);
        options.onConnectionChange?.(state);
      },
    });

    setClient(sseClient);

    return () => {
      sseClient.disconnect();
    };
  }, [jobId]);

  const connect = React.useCallback(() => {
    client?.connect();
  }, [client]);

  const disconnect = React.useCallback(() => {
    client?.disconnect();
  }, [client]);

  return {
    client,
    connectionState,
    connect,
    disconnect,
  };
}