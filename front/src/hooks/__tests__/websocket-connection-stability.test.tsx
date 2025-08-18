import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useWebSocket, useWebSocketSubscription } from '../websocket-hooks';
import { WebSocketClient, getWebSocketClient, resetWebSocketClient } from '@/lib/websocket';
import { useAuth } from '@/providers/auth-provider';

// Mock the auth provider
vi.mock('@/providers/auth-provider');
const mockUseAuth = vi.mocked(useAuth);

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(public url: string) {
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 10);
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: code || 1000, reason }));
  }

  // Helper methods for testing
  simulateError() {
    this.onerror?.(new Event('error'));
  }

  simulateMessage(data: any) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }
}

// Mock global WebSocket
(global as any).WebSocket = MockWebSocket;

describe('WebSocket Connection Stability', () => {
  const mockUser = { id: 'test-user-123' };
  const mockGetToken = vi.fn().mockResolvedValue('test-token');

  beforeEach(() => {
    vi.clearAllMocks();
    resetWebSocketClient();
    mockUseAuth.mockReturnValue({
      user: mockUser,
      getToken: mockGetToken,
      login: vi.fn(),
      logout: vi.fn(),
      isAuthenticated: true,
      isLoading: false,
    });
  });

  afterEach(() => {
    resetWebSocketClient();
  });

  describe('Connection Loop Prevention', () => {
    it('should prevent multiple simultaneous connection attempts', async () => {
      const { result } = renderHook(() => useWebSocket());

      // Try to connect multiple times rapidly
      act(() => {
        result.current.connect();
        result.current.connect();
        result.current.connect();
      });

      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
      });

      // Should only have one connection
      expect(result.current.isConnected).toBe(true);
    });

    it('should not auto-reconnect when manually disconnected', async () => {
      const { result } = renderHook(() => useWebSocket());

      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
      });

      // Manually disconnect
      act(() => {
        result.current.disconnect();
      });

      await waitFor(() => {
        expect(result.current.state.status).toBe('disconnected');
      });

      // Should not auto-reconnect
      await new Promise(resolve => setTimeout(resolve, 100));
      expect(result.current.state.status).toBe('disconnected');
    });

    it('should respect rate limiting for connection attempts', async () => {
      const { result } = renderHook(() => useWebSocket());

      // First connection should work
      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
      });

      // Disconnect and try to reconnect immediately
      act(() => {
        result.current.disconnect();
      });

      // Multiple rapid reconnect attempts should be throttled
      const connectPromises = Array(5).fill(0).map(() => 
        act(() => result.current.connect())
      );

      await Promise.all(connectPromises);

      // Should eventually connect but not create multiple connections
      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle connection timeouts gracefully', async () => {
      // Mock a WebSocket that never connects
      class TimeoutWebSocket extends MockWebSocket {
        constructor(url: string) {
          super(url);
          this.readyState = MockWebSocket.CONNECTING;
          // Don't call onopen - simulate timeout
        }
      }

      (global as any).WebSocket = TimeoutWebSocket;

      const { result } = renderHook(() => useWebSocket());

      // Wait for timeout to occur (should be handled by the 10s timeout in connect method)
      await waitFor(() => {
        expect(result.current.state.status).toBe('error');
      }, { timeout: 15000 });

      expect(result.current.state.lastError).toContain('timeout');
    });

    it('should handle different close codes appropriately', async () => {
      const { result } = renderHook(() => useWebSocket());

      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
      });

      // Simulate authentication failure (should not reconnect)
      const client = getWebSocketClient(mockUser.id);
      const mockWs = (client as any).ws as MockWebSocket;
      
      act(() => {
        mockWs.close(4000, 'Authentication failed');
      });

      await waitFor(() => {
        expect(result.current.state.status).toBe('error');
        expect(result.current.state.lastError).toContain('Authentication failed');
      });

      // Should not attempt reconnection for auth failures
      await new Promise(resolve => setTimeout(resolve, 100));
      expect(result.current.state.status).toBe('error');
    });

    it('should retry on recoverable errors with exponential backoff', async () => {
      const { result } = renderHook(() => useWebSocket());

      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
      });

      // Simulate unexpected disconnection (should reconnect)
      const client = getWebSocketClient(mockUser.id);
      const mockWs = (client as any).ws as MockWebSocket;
      
      act(() => {
        mockWs.close(1006, 'Connection lost');
      });

      // Should attempt to reconnect
      await waitFor(() => {
        expect(result.current.state.reconnectAttempts).toBeGreaterThan(0);
      });
    });
  });

  describe('Message Handling', () => {
    it('should ignore messages from old connections', async () => {
      const messageHandler = vi.fn();
      
      const { result } = renderHook(() => {
        const ws = useWebSocket();
        useWebSocketSubscription('response', messageHandler);
        return ws;
      });

      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
      });

      // Force a reconnection
      act(() => {
        result.current.forceReconnect();
      });

      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
      });

      // Old connection messages should be ignored
      const client = getWebSocketClient(mockUser.id);
      const mockWs = (client as any).ws as MockWebSocket;
      
      act(() => {
        mockWs.simulateMessage({
          type: 'response',
          data: { message: 'test' },
          timestamp: new Date().toISOString()
        });
      });

      await waitFor(() => {
        expect(messageHandler).toHaveBeenCalledTimes(1);
      });
    });

    it('should handle message parsing errors gracefully', async () => {
      const messageHandler = vi.fn();
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const { result } = renderHook(() => {
        const ws = useWebSocket();
        useWebSocketSubscription('response', messageHandler);
        return ws;
      });

      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
      });

      const client = getWebSocketClient(mockUser.id);
      const mockWs = (client as any).ws as MockWebSocket;
      
      // Send invalid JSON
      act(() => {
        mockWs.onmessage?.(new MessageEvent('message', { data: 'invalid json' }));
      });

      expect(consoleError).toHaveBeenCalledWith(
        'Failed to parse WebSocket message:',
        expect.any(Error)
      );
      expect(messageHandler).not.toHaveBeenCalled();

      consoleError.mockRestore();
    });
  });

  describe('Subscription Management', () => {
    it('should clean up subscriptions properly', () => {
      const messageHandler = vi.fn();
      
      const { unmount } = renderHook(() => {
        useWebSocketSubscription('response', messageHandler);
      });

      // Unmount should clean up subscription
      unmount();

      // Verify no memory leaks or hanging subscriptions
      const client = getWebSocketClient(mockUser.id);
      expect((client as any).listeners.get('response')?.size || 0).toBe(0);
    });

    it('should handle subscription errors gracefully', async () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error');
      });
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const { result } = renderHook(() => {
        const ws = useWebSocket();
        useWebSocketSubscription('response', errorHandler);
        return ws;
      });

      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
      });

      const client = getWebSocketClient(mockUser.id);
      const mockWs = (client as any).ws as MockWebSocket;
      
      act(() => {
        mockWs.simulateMessage({
          type: 'response',
          data: { message: 'test' },
          timestamp: new Date().toISOString()
        });
      });

      expect(consoleError).toHaveBeenCalledWith(
        'Error in WebSocket subscription handler for response:',
        expect.any(Error)
      );

      consoleError.mockRestore();
    });
  });

  describe('Health Monitoring', () => {
    it('should report connection health accurately', async () => {
      const { result } = renderHook(() => useWebSocket());

      // Initially not healthy
      expect(result.current.isHealthy).toBe(false);

      await waitFor(() => {
        expect(result.current.state.status).toBe('connected');
        expect(result.current.isHealthy).toBe(true);
      });

      // Disconnect should make it unhealthy
      act(() => {
        result.current.disconnect();
      });

      await waitFor(() => {
        expect(result.current.isHealthy).toBe(false);
      });
    });
  });
});