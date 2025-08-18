import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WebSocketClient } from '@/lib/websocket';

// Manual verification test for WebSocket stability improvements
describe('WebSocket Stability Manual Verification', () => {
  let client: WebSocketClient;

  beforeEach(() => {
    client = new WebSocketClient('ws://test.com');
  });

  afterEach(() => {
    client.disconnect();
  });

  it('should have connection loop prevention flags', () => {
    // Verify the client has the new connection loop prevention properties
    expect((client as any).isConnecting).toBe(false);
    expect((client as any).isManuallyDisconnected).toBe(false);
    expect((client as any).connectionId).toBe(0);
  });

  it('should have new helper methods for stability', () => {
    // Verify new methods exist
    expect(typeof client.reset).toBe('function');
    expect(typeof client.isHealthy).toBe('function');
  });

  it('should have improved error handling methods', () => {
    // Verify private methods exist (check via prototype)
    const prototype = Object.getPrototypeOf(client);
    expect(typeof (prototype as any).shouldAttemptReconnect).toBe('function');
    expect(typeof (prototype as any).getCloseErrorMessage).toBe('function');
    expect(typeof (prototype as any).handleConnectionTimeout).toBe('function');
  });

  it('should reset state properly', () => {
    // Set some state
    (client as any).reconnectAttempts = 5;
    (client as any).isConnecting = true;
    (client as any).messageQueue = [{ type: 'test', data: {}, timestamp: '2024-01-01' }];

    // Reset should clear everything
    client.reset();

    expect((client as any).reconnectAttempts).toBe(0);
    expect((client as any).isConnecting).toBe(false);
    expect((client as any).isManuallyDisconnected).toBe(false);
    expect((client as any).messageQueue).toEqual([]);
    expect((client as any).connectionId).toBeGreaterThan(0);
  });

  it('should report health status correctly', () => {
    // Initially not healthy (no WebSocket)
    expect(client.isHealthy()).toBe(false);

    // Mock a WebSocket in OPEN state
    (client as any).ws = { 
      readyState: 1, // WebSocket.OPEN
      close: vi.fn()
    };
    (client as any).isConnecting = false;
    expect(client.isHealthy()).toBe(true);

    // Mock connecting state
    (client as any).isConnecting = true;
    expect(client.isHealthy()).toBe(false);

    // Mock closed state
    (client as any).ws = { 
      readyState: 3, // WebSocket.CLOSED
      close: vi.fn()
    };
    (client as any).isConnecting = false;
    expect(client.isHealthy()).toBe(false);
  });

  it('should have proper close code handling', () => {
    const shouldAttemptReconnect = (client as any).shouldAttemptReconnect.bind(client);
    const getCloseErrorMessage = (client as any).getCloseErrorMessage.bind(client);

    // Should not reconnect for auth failures
    expect(shouldAttemptReconnect(4000)).toBe(false);
    expect(shouldAttemptReconnect(4001)).toBe(false);
    expect(shouldAttemptReconnect(4003)).toBe(false);

    // Should reconnect for connection issues
    expect(shouldAttemptReconnect(1006)).toBe(true);
    expect(shouldAttemptReconnect(1011)).toBe(true);

    // Should have appropriate error messages
    expect(getCloseErrorMessage(4000)).toBe('Authentication failed');
    expect(getCloseErrorMessage(1006)).toBe('Connection lost unexpectedly');
    expect(getCloseErrorMessage(1011)).toBe('Server error occurred');
  });

  it('should handle connection ID tracking', () => {
    const initialId = (client as any).connectionId;
    
    // Reset should increment connection ID
    client.reset();
    expect((client as any).connectionId).toBe(initialId + 1);
    
    // Another reset should increment again
    client.reset();
    expect((client as any).connectionId).toBe(initialId + 2);
  });

  it('should have manual disconnect tracking', () => {
    expect((client as any).isManuallyDisconnected).toBe(false);
    
    // Disconnect should set manual flag
    client.disconnect();
    expect((client as any).isManuallyDisconnected).toBe(true);
    
    // Reset should clear manual flag
    client.reset();
    expect((client as any).isManuallyDisconnected).toBe(false);
  });
});