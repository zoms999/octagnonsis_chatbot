import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthDebugger } from '../auth-debug';
import { ChatApiDebugger } from '../chat-api-debug';

// Mock console methods
const mockConsole = {
  log: vi.fn(),
  group: vi.fn(),
  groupEnd: vi.fn(),
  error: vi.fn(),
  warn: vi.fn(),
};

// Mock global console
Object.assign(console, mockConsole);

describe('Debug Utilities', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('AuthDebugger', () => {
    it('should extract user ID from user.id field', () => {
      const user = { id: 'test-123', name: 'Test User' };
      const userId = AuthDebugger.extractUserId(user);
      expect(userId).toBe('test-123');
    });

    it('should extract user ID from user.user_id field', () => {
      const user = { user_id: 'legacy-456', name: 'Legacy User' };
      const userId = AuthDebugger.extractUserId(user);
      expect(userId).toBe('legacy-456');
    });

    it('should return null for user without ID', () => {
      const user = { name: 'No ID User' };
      const userId = AuthDebugger.extractUserId(user);
      expect(userId).toBe(null);
    });

    it('should return null for null user', () => {
      const userId = AuthDebugger.extractUserId(null);
      expect(userId).toBe(null);
    });

    it('should validate auth state correctly', () => {
      const user = { id: 'test-123', name: 'Test User' };
      const debugInfo = AuthDebugger.validateAuthState(user);
      
      expect(debugInfo).toHaveProperty('userId', 'test-123');
      expect(debugInfo).toHaveProperty('userIdSource', 'id');
      expect(debugInfo).toHaveProperty('isAuthenticated');
      expect(debugInfo).toHaveProperty('tokenExists');
      expect(debugInfo).toHaveProperty('tokenValid');
    });

    it('should log auth state without errors', () => {
      const user = { id: 'test-123', name: 'Test User' };
      
      expect(() => {
        AuthDebugger.logAuthState(user);
      }).not.toThrow();
      
      expect(mockConsole.group).toHaveBeenCalled();
      expect(mockConsole.log).toHaveBeenCalled();
      expect(mockConsole.groupEnd).toHaveBeenCalled();
    });
  });

  describe('ChatApiDebugger', () => {
    it('should validate payload correctly', () => {
      const validPayload = {
        question: 'Test question',
        conversation_id: 'conv-123',
        user_id: 'user-456'
      };
      
      const errors = ChatApiDebugger.validatePayload(validPayload);
      expect(errors).toHaveLength(0);
    });

    it('should detect missing question', () => {
      const invalidPayload = {
        conversation_id: 'conv-123',
        user_id: 'user-456'
      };
      
      const errors = ChatApiDebugger.validatePayload(invalidPayload);
      expect(errors).toContain('Missing or invalid "question" field');
    });

    it('should detect empty question', () => {
      const invalidPayload = {
        question: '   ',
        conversation_id: 'conv-123',
        user_id: 'user-456'
      };
      
      const errors = ChatApiDebugger.validatePayload(invalidPayload);
      expect(errors).toContain('Question field is empty');
    });

    it('should handle null payload', () => {
      const errors = ChatApiDebugger.validatePayload(null);
      expect(errors).toContain('Payload is null or undefined');
    });
  });
});