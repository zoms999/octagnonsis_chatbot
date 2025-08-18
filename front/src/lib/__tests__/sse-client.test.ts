/**
 * Tests for SSE client functionality
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SSEClient, SSEProgressData } from '../sse-client';

// Mock EventSource
class MockEventSource {
  public onopen: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public readyState: number = EventSource.CONNECTING;
  
  constructor(public url: string) {}
  
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  
  close() {
    this.readyState = MockEventSource.CLOSED;
  }
  
  // Test helpers
  simulateOpen() {
    this.readyState = MockEventSource.OPEN;
    this.onopen?.(new Event('open'));
  }
  
  simulateMessage(data: SSEProgressData) {
    const event = new MessageEvent('message', {
      data: JSON.stringify(data),
    });
    this.onmessage?.(event);
  }
  
  simulateError() {
    this.readyState = MockEventSource.CLOSED;
    this.onerror?.(new Event('error'));
  }
}

// Mock global EventSource
global.EventSource = MockEventSource as any;
global.EventSource.CONNECTING = 0;
global.EventSource.OPEN = 1;
global.EventSource.CLOSED = 2;

describe('SSEClient', () => {
  let client: SSEClient;
  let mockOnProgress: ReturnType<typeof vi.fn>;
  let mockOnError: ReturnType<typeof vi.fn>;
  let mockOnConnectionChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnProgress = vi.fn();
    mockOnError = vi.fn();
    mockOnConnectionChange = vi.fn();
    
    client = new SSEClient('test-job-id', {
      onProgress: mockOnProgress,
      onError: mockOnError,
      onConnectionChange: mockOnConnectionChange,
      maxReconnectAttempts: 3,
      reconnectDelay: 100,
    });
  });

  afterEach(() => {
    client.disconnect();
  });

  describe('connection management', () => {
    it('should create SSE connection when connect is called', () => {
      client.connect();
      
      // The connection starts as connecting, so isConnected should be false initially
      expect((client as any).eventSource).toBeDefined();
      expect((client as any).eventSource.readyState).toBe(MockEventSource.CONNECTING);
    });

    it('should handle successful connection', () => {
      client.connect();
      const eventSource = (client as any).eventSource as MockEventSource;
      
      eventSource.simulateOpen();
      
      expect(mockOnConnectionChange).toHaveBeenCalledWith({
        isConnected: true,
        reconnectAttempts: 0,
      });
    });

    it('should handle connection errors', () => {
      client.connect();
      const eventSource = (client as any).eventSource as MockEventSource;
      
      eventSource.simulateError();
      
      expect(mockOnError).toHaveBeenCalled();
      expect(mockOnConnectionChange).toHaveBeenCalledWith({
        isConnected: false,
        reconnectAttempts: 0,
        lastError: 'Connection error',
      });
    });

    it('should disconnect properly', () => {
      client.connect();
      const eventSource = (client as any).eventSource as MockEventSource;
      
      client.disconnect();
      
      expect(eventSource.readyState).toBe(MockEventSource.CLOSED);
      expect(mockOnConnectionChange).toHaveBeenCalledWith({
        isConnected: false,
        reconnectAttempts: 0,
      });
    });
  });

  describe('message handling', () => {
    it('should handle progress messages', () => {
      client.connect();
      const eventSource = (client as any).eventSource as MockEventSource;
      
      const progressData: SSEProgressData = {
        job_id: 'test-job-id',
        progress: 50,
        current_step: 'Processing documents',
        status: 'running',
      };
      
      eventSource.simulateMessage(progressData);
      
      expect(mockOnProgress).toHaveBeenCalledWith(progressData);
    });

    it('should handle malformed messages gracefully', () => {
      client.connect();
      const eventSource = (client as any).eventSource as MockEventSource;
      
      // Simulate malformed JSON
      const event = new MessageEvent('message', {
        data: 'invalid json',
      });
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      eventSource.onmessage?.(event);
      
      expect(consoleSpy).toHaveBeenCalledWith('Failed to parse SSE message:', expect.any(Error));
      expect(mockOnProgress).not.toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });
  });

  describe('reconnection logic', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should attempt reconnection on error', () => {
      client.connect();
      const eventSource = (client as any).eventSource as MockEventSource;
      
      eventSource.simulateError();
      
      // Fast-forward time to trigger reconnection
      vi.advanceTimersByTime(100);
      
      // Should have attempted reconnection
      expect((client as any).reconnectAttempts).toBe(1);
    });

    it('should stop reconnecting after max attempts', () => {
      client.connect();
      
      // Simulate multiple errors
      for (let i = 0; i < 5; i++) {
        const eventSource = (client as any).eventSource as MockEventSource;
        eventSource.simulateError();
        vi.advanceTimersByTime(1000);
      }
      
      expect((client as any).reconnectAttempts).toBe(3); // maxReconnectAttempts
    });

    it('should not reconnect when manually disconnected', () => {
      client.connect();
      const eventSource = (client as any).eventSource as MockEventSource;
      
      client.disconnect();
      eventSource.simulateError();
      
      vi.advanceTimersByTime(1000);
      
      expect((client as any).reconnectAttempts).toBe(0);
    });
  });

  describe('authentication', () => {
    beforeEach(() => {
      // Mock localStorage
      Object.defineProperty(window, 'localStorage', {
        value: {
          getItem: vi.fn(),
          setItem: vi.fn(),
          removeItem: vi.fn(),
        },
        writable: true,
      });
    });

    it('should include auth token in URL when available', () => {
      const mockToken = 'test-auth-token';
      (window.localStorage.getItem as any).mockReturnValue(mockToken);
      
      client.connect();
      const eventSource = (client as any).eventSource as MockEventSource;
      
      expect(eventSource.url).toContain(`token=${encodeURIComponent(mockToken)}`);
    });

    it('should work without auth token', () => {
      (window.localStorage.getItem as any).mockReturnValue(null);
      
      client.connect();
      const eventSource = (client as any).eventSource as MockEventSource;
      
      expect(eventSource.url).not.toContain('token=');
    });
  });

  describe('connection state', () => {
    it('should return correct connection state', () => {
      // Initially no connection
      expect(client.getConnectionState()).toEqual({
        isConnected: false,
        reconnectAttempts: 0,
      });
      
      client.connect();
      
      // After connecting but before open event
      expect(client.getConnectionState().isConnected).toBe(false);
      
      const eventSource = (client as any).eventSource as MockEventSource;
      eventSource.simulateOpen();
      
      // After open event
      expect(client.getConnectionState().isConnected).toBe(true);
    });
  });
});