import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WebSocketClient } from '@/lib/websocket';

// Simple integration test to verify WebSocket stability improvements
describe('WebSocket Stability Integration', () => {
  let client: WebSocketClient;
  let mockWebSocket: any;

  beforeEach(() => {
    // Mock WebSocket constructor
    mockWebSocket = {
      readyState: 0, // CONNECTING
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onclose: null,
      onerror: null,
      onmessage: null,
    };

    (global as any).WebSocket = vi.fn(() => mockWebSocket);
    client = new WebSocketClient('ws://test.com');
  });

  afterEach(() => {
    client.disconnect();
  });

  describe('Connection Loop Prevention', () => {
    it('should prevent multiple simultaneous connections', () => {
      // First connection attempt
      client.connect('token1');
      expect(global.WebSocket).toHaveBeenCalledTimes(1);

      // Second connection attempt should be ignored
      client.connect('token2');
      expect(global.WebSocket).toHaveBeenCalledTimes(1);

      // Third connection attempt should be ignored
      client.connect('token3');
      expect(global.WebSocket).toHaveBeenCalledTimes(1);
    });

    it('should allow reconnection after disconnect', () => {
      // First connection
      client.connect('token1');
      expect(global.WebSocket).toHaveBeenCalledTimes(1);

      // Disconnect
      client.disconnect();

      // Should allow new connection after disconnect
      client.connect('token2');
      expect(global.WebSocket).toHaveBeenCalledTimes(2);
    });

    it('should track connection IDs to prevent stale events', () => {
      const stateListener = vi.fn();
      client.subscribeToState(stateListener);

      // Start first connection
      client.connect('token1');
      const firstConnectionId = (client as any).connectionId;

      // Simulate connection success
      mockWebSocket.readyState = 1; // OPEN
      mockWebSocket.onopen?.(new Event('open'));

      expect(stateListener).toHaveBeenCalledWith({
        status: 'connected',
        reconnectAttempts: 0,
      });

      // Reset mock
      stateListener.mockClear();

      // Start second connection (force reconnect)
      client.reset();
      client.connect('token2');
      const secondConnectionId = (client as any).connectionId;

      expect(secondConnectionId).toBeGreaterThan(firstConnectionId);

      // Simulate old connection trying to fire events (should be ignored)
      const oldOnOpen = mockWebSocket.onopen;
      mockWebSocket.onopen = (event: Event) => oldOnOpen?.(event, firstConnectionId);
      mockWebSocket.onopen(new Event('open'));

      // Should not trigger state change for old connection
      expect(stateListener).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should handle different close codes appropriately', () => {
      const stateListener = vi.fn();
      client.subscribeToState(stateListener);

      client.connect('token');
      
      // Simulate authentication failure (should not reconnect)
      mockWebSocket.onclose?.(new CloseEvent('close', { code: 4000, reason: 'Auth failed' }));

      expect(stateListener).toHaveBeenCalledWith({
        status: 'error',
        lastError: 'Authentication failed',
        reconnectAttempts: 0,
      });
    });

    it('should schedule reconnection for recoverable errors', () => {
      const stateListener = vi.fn();
      client.subscribeToState(stateListener);

      client.connect('token');
      
      // Simulate unexpected disconnection (should reconnect)
      mockWebSocket.onclose?.(new CloseEvent('close', { code: 1006, reason: 'Connection lost' }));

      expect(stateListener).toHaveBeenCalledWith({
        status: 'connecting',
        reconnectAttempts: 1,
      });
    });

    it('should not reconnect when manually disconnected', () => {
      const stateListener = vi.fn();
      client.subscribeToState(stateListener);

      client.connect('token');
      client.disconnect(); // Manual disconnect

      stateListener.mockClear();

      // Simulate close event after manual disconnect
      mockWebSocket.onclose?.(new CloseEvent('close', { code: 1000, reason: 'Normal closure' }));

      expect(stateListener).toHaveBeenCalledWith({
        status: 'disconnected',
        reconnectAttempts: 0,
      });

      // Should not schedule reconnection
      expect((client as any).reconnectTimer).toBeNull();
    });
  });

  describe('Message Handling', () => {
    it('should handle message parsing errors gracefully', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      const messageListener = vi.fn();

      client.subscribe('test', messageListener);
      client.connect('token');

      // Simulate invalid JSON message
      mockWebSocket.onmessage?.(new MessageEvent('message', { data: 'invalid json' }));

      expect(consoleError).toHaveBeenCalledWith(
        'Failed to parse WebSocket message:',
        expect.any(Error)
      );
      expect(messageListener).not.toHaveBeenCalled();

      consoleError.mockRestore();
    });

    it('should handle listener errors gracefully', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      const errorListener = vi.fn(() => {
        throw new Error('Listener error');
      });

      client.subscribe('test', errorListener);
      client.connect('token');

      // Simulate valid message
      mockWebSocket.onmessage?.(new MessageEvent('message', { 
        data: JSON.stringify({
          type: 'test',
          data: { message: 'hello' },
          timestamp: new Date().toISOString()
        })
      }));

      expect(consoleError).toHaveBeenCalledWith(
        'Error in message listener for test:',
        expect.any(Error)
      );

      consoleError.mockRestore();
    });
  });

  describe('Health Monitoring', () => {
    it('should report connection health accurately', () => {
      // Initially not healthy
      expect(client.isHealthy()).toBe(false);

      // Connect
      client.connect('token');
      expect(client.isHealthy()).toBe(false); // Still connecting

      // Simulate connection success
      mockWebSocket.readyState = 1; // OPEN
      expect(client.isHealthy()).toBe(true);

      // Disconnect
      client.disconnect();
      mockWebSocket.readyState = 3; // CLOSED
      expect(client.isHealthy()).toBe(false);
    });
  });

  describe('State Management', () => {
    it('should reset connection state properly', () => {
      const stateListener = vi.fn();
      client.subscribeToState(stateListener);

      // Connect and simulate some reconnect attempts
      client.connect('token');
      (client as any).reconnectAttempts = 3;

      // Reset should clear state
      client.reset();

      expect((client as any).reconnectAttempts).toBe(0);
      expect((client as any).isConnecting).toBe(false);
      expect((client as any).isManuallyDisconnected).toBe(false);
      expect((client as any).messageQueue).toEqual([]);
    });

    it('should handle state listener errors gracefully', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      const errorListener = vi.fn(() => {
        throw new Error('State listener error');
      });

      client.subscribeToState(errorListener);
      client.connect('token');

      expect(consoleError).toHaveBeenCalledWith(
        'Error in state listener:',
        expect.any(Error)
      );

      consoleError.mockRestore();
    });
  });
});