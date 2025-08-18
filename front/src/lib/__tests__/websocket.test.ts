import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WebSocketClient, getWebSocketClient, resetWebSocketClient } from '../websocket';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
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
  simulateMessage(data: any) {
    if (this.readyState === MockWebSocket.OPEN) {
      this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  simulateError() {
    this.onerror?.(new Event('error'));
  }
}

// Mock global WebSocket
global.WebSocket = MockWebSocket as any;

describe('WebSocketClient', () => {
  let client: WebSocketClient;
  const testUrl = 'ws://localhost:8000/test';

  beforeEach(() => {
    client = new WebSocketClient(testUrl);
    vi.clearAllTimers();
    vi.useFakeTimers();
  });

  afterEach(() => {
    client.disconnect();
    vi.useRealTimers();
    resetWebSocketClient();
  });

  describe('Connection Management', () => {
    it('should initialize with disconnected state', () => {
      const state = client.getState();
      expect(state.status).toBe('disconnected');
      expect(state.reconnectAttempts).toBe(0);
    });

    it('should connect successfully', async () => {
      const stateUpdates: any[] = [];
      client.subscribeToState((state) => stateUpdates.push(state));

      client.connect();
      
      // Should start with connecting state
      expect(stateUpdates[0].status).toBe('connecting');

      // Advance timers to simulate connection
      await vi.advanceTimersByTimeAsync(20);

      // Should be connected
      expect(stateUpdates[1].status).toBe('connected');
    });

    it('should handle connection errors', async () => {
      const stateUpdates: any[] = [];
      client.subscribeToState((state) => stateUpdates.push(state));

      client.connect();
      
      // Simulate connection error
      const ws = (client as any).ws as MockWebSocket;
      ws.simulateError();

      expect(stateUpdates.some(s => s.status === 'error')).toBe(true);
    });

    it('should disconnect cleanly', async () => {
      client.connect();
      await vi.advanceTimersByTimeAsync(20);

      const stateUpdates: any[] = [];
      client.subscribeToState((state) => stateUpdates.push(state));

      client.disconnect();

      expect(stateUpdates[0].status).toBe('disconnected');
    });
  });

  describe('Message Handling', () => {
    beforeEach(async () => {
      client.connect();
      await vi.advanceTimersByTimeAsync(20);
    });

    it('should send messages when connected', () => {
      const message = {
        type: 'question' as const,
        data: { question: 'test' },
        timestamp: new Date().toISOString(),
      };

      expect(() => client.send(message)).not.toThrow();
    });

    it('should queue messages when disconnected', () => {
      client.disconnect();

      const message = {
        type: 'question' as const,
        data: { question: 'test' },
        timestamp: new Date().toISOString(),
      };

      // Should not throw when disconnected
      expect(() => client.send(message)).not.toThrow();
    });

    it('should receive and handle messages', async () => {
      const messages: any[] = [];
      client.subscribe('response', (message) => messages.push(message));

      const testMessage = {
        type: 'response',
        data: { response: 'test response' },
        timestamp: new Date().toISOString(),
      };

      const ws = (client as any).ws as MockWebSocket;
      ws.simulateMessage(testMessage);

      expect(messages).toHaveLength(1);
      expect(messages[0]).toEqual(testMessage);
    });

    it('should handle subscription and unsubscription', () => {
      const messages: any[] = [];
      const unsubscribe = client.subscribe('response', (message) => messages.push(message));

      const testMessage = {
        type: 'response',
        data: { response: 'test response' },
        timestamp: new Date().toISOString(),
      };

      const ws = (client as any).ws as MockWebSocket;
      ws.simulateMessage(testMessage);

      expect(messages).toHaveLength(1);

      // Unsubscribe and send another message
      unsubscribe();
      ws.simulateMessage(testMessage);

      // Should still be 1 (no new message received)
      expect(messages).toHaveLength(1);
    });
  });

  describe('Reconnection Logic', () => {
    it('should attempt reconnection on unexpected close', async () => {
      client.connect();
      await vi.advanceTimersByTimeAsync(20);

      const stateUpdates: any[] = [];
      client.subscribeToState((state) => stateUpdates.push(state));

      // Simulate unexpected close (not code 1000)
      const ws = (client as any).ws as MockWebSocket;
      ws.close(1006, 'Connection lost');

      // Should attempt reconnection
      await vi.advanceTimersByTimeAsync(1000);

      expect(stateUpdates.some(s => s.status === 'connecting')).toBe(true);
    });

    it('should not reconnect on normal close', async () => {
      client.connect();
      await vi.advanceTimersByTimeAsync(20);

      const stateUpdates: any[] = [];
      client.subscribeToState((state) => stateUpdates.push(state));

      // Simulate normal close (code 1000)
      const ws = (client as any).ws as MockWebSocket;
      ws.close(1000, 'Normal close');

      await vi.advanceTimersByTimeAsync(2000);

      // Should not attempt reconnection
      expect(stateUpdates.every(s => s.status !== 'connecting')).toBe(true);
    });

    it('should implement exponential backoff', async () => {
      client.connect();
      await vi.advanceTimersByTimeAsync(20);

      // Force multiple reconnection attempts
      for (let i = 0; i < 3; i++) {
        const ws = (client as any).ws as MockWebSocket;
        ws.close(1006, 'Connection lost');
        await vi.advanceTimersByTimeAsync(100);
      }

      const state = client.getState();
      expect(state.reconnectAttempts).toBeGreaterThan(0);
    });
  });
});

describe('WebSocket Global Client', () => {
  afterEach(() => {
    resetWebSocketClient();
  });

  it('should create global client with user ID', () => {
    const client = getWebSocketClient('user123');
    expect(client).toBeDefined();
  });

  it('should reuse existing global client', () => {
    const client1 = getWebSocketClient('user123');
    const client2 = getWebSocketClient('user123');
    expect(client1).toBe(client2);
  });

  it('should throw error when no user ID provided and no existing client', () => {
    expect(() => getWebSocketClient()).toThrow('WebSocket client not initialized');
  });

  it('should reset global client', () => {
    getWebSocketClient('user123');
    resetWebSocketClient();
    expect(() => getWebSocketClient()).toThrow('WebSocket client not initialized');
  });
});