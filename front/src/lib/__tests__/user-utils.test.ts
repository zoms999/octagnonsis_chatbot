import { describe, it, expect } from 'vitest';
import { 
  extractUserId, 
  hasValidUserId, 
  getUserIdSource, 
  getUserIdDebugInfo 
} from '../user-utils';
import { AuthUser } from '../types';

describe('user-utils', () => {
  describe('extractUserId', () => {
    it('should extract user ID from standard id field', () => {
      const user: AuthUser = {
        id: 'user-123',
        name: 'Test User',
        type: 'personal'
      };
      
      const userId = extractUserId(user);
      expect(userId).toBe('user-123');
    });

    it('should extract user ID from legacy user_id field', () => {
      const user = {
        user_id: 'legacy-456',
        name: 'Legacy User',
        type: 'personal'
      } as any;
      
      const userId = extractUserId(user);
      expect(userId).toBe('legacy-456');
    });

    it('should prefer id over user_id when both exist', () => {
      const user = {
        id: 'current-123',
        user_id: 'legacy-456',
        name: 'Mixed User',
        type: 'personal'
      } as any;
      
      const userId = extractUserId(user);
      expect(userId).toBe('current-123');
    });

    it('should return null for null user', () => {
      const userId = extractUserId(null);
      expect(userId).toBeNull();
    });

    it('should return null for undefined user', () => {
      const userId = extractUserId(undefined);
      expect(userId).toBeNull();
    });

    it('should return null for user without id fields', () => {
      const user = {
        name: 'No ID User',
        type: 'personal'
      } as any;
      
      const userId = extractUserId(user);
      expect(userId).toBeNull();
    });
  });

  describe('hasValidUserId', () => {
    it('should return true for user with valid id', () => {
      const user: AuthUser = {
        id: 'user-123',
        name: 'Test User',
        type: 'personal'
      };
      
      expect(hasValidUserId(user)).toBe(true);
    });

    it('should return true for user with legacy user_id', () => {
      const user = {
        user_id: 'legacy-456',
        name: 'Legacy User',
        type: 'personal'
      } as any;
      
      expect(hasValidUserId(user)).toBe(true);
    });

    it('should return false for null user', () => {
      expect(hasValidUserId(null)).toBe(false);
    });

    it('should return false for user without id fields', () => {
      const user = {
        name: 'No ID User',
        type: 'personal'
      } as any;
      
      expect(hasValidUserId(user)).toBe(false);
    });
  });

  describe('getUserIdSource', () => {
    it('should return "id" for standard user', () => {
      const user: AuthUser = {
        id: 'user-123',
        name: 'Test User',
        type: 'personal'
      };
      
      expect(getUserIdSource(user)).toBe('id');
    });

    it('should return "user_id" for legacy user', () => {
      const user = {
        user_id: 'legacy-456',
        name: 'Legacy User',
        type: 'personal'
      } as any;
      
      expect(getUserIdSource(user)).toBe('user_id');
    });

    it('should return "id" when both fields exist', () => {
      const user = {
        id: 'current-123',
        user_id: 'legacy-456',
        name: 'Mixed User',
        type: 'personal'
      } as any;
      
      expect(getUserIdSource(user)).toBe('id');
    });

    it('should return "missing" for null user', () => {
      expect(getUserIdSource(null)).toBe('missing');
    });

    it('should return "missing" for user without id fields', () => {
      const user = {
        name: 'No ID User',
        type: 'personal'
      } as any;
      
      expect(getUserIdSource(user)).toBe('missing');
    });
  });

  describe('getUserIdDebugInfo', () => {
    it('should return complete debug info for valid user', () => {
      const user: AuthUser = {
        id: 'user-123',
        name: 'Test User',
        type: 'personal'
      };
      
      const debugInfo = getUserIdDebugInfo(user);
      expect(debugInfo).toEqual({
        hasUser: true,
        userId: 'user-123',
        source: 'id',
        isValid: true
      });
    });

    it('should return debug info for legacy user', () => {
      const user = {
        user_id: 'legacy-456',
        name: 'Legacy User',
        type: 'personal'
      } as any;
      
      const debugInfo = getUserIdDebugInfo(user);
      expect(debugInfo).toEqual({
        hasUser: true,
        userId: 'legacy-456',
        source: 'user_id',
        isValid: true
      });
    });

    it('should return debug info for null user', () => {
      const debugInfo = getUserIdDebugInfo(null);
      expect(debugInfo).toEqual({
        hasUser: false,
        userId: null,
        source: 'missing',
        isValid: false
      });
    });

    it('should return debug info for user without id fields', () => {
      const user = {
        name: 'No ID User',
        type: 'personal'
      } as any;
      
      const debugInfo = getUserIdDebugInfo(user);
      expect(debugInfo).toEqual({
        hasUser: true,
        userId: null,
        source: 'missing',
        isValid: false
      });
    });
  });
});