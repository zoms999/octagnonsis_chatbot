/**
 * User utility functions for consistent user data handling
 */

import { AuthUser } from '@/lib/types';

/**
 * Extracts user ID consistently from user object
 * Handles both current (id) and legacy (user_id) field names for backward compatibility
 */
export function extractUserId(user: AuthUser | null | undefined): string | null {
  if (!user) {
    return null;
  }

  // Primary field: id (current standard)
  if (user.id) {
    return user.id;
  }

  // Legacy fallback: user_id (for backward compatibility)
  const legacyUser = user as any;
  if (legacyUser.user_id) {
    console.warn('User ID found in legacy "user_id" field. Consider updating backend to use "id" field.');
    return legacyUser.user_id;
  }

  return null;
}

/**
 * Validates that a user object has a valid ID
 */
export function hasValidUserId(user: AuthUser | null | undefined): user is AuthUser {
  return extractUserId(user) !== null;
}

/**
 * Gets user ID source for debugging purposes
 */
export function getUserIdSource(user: AuthUser | null | undefined): 'id' | 'user_id' | 'missing' {
  if (!user) {
    return 'missing';
  }

  if (user.id) {
    return 'id';
  }

  const legacyUser = user as any;
  if (legacyUser.user_id) {
    return 'user_id';
  }

  return 'missing';
}

/**
 * Debug information about user ID extraction
 */
export interface UserIdDebugInfo {
  hasUser: boolean;
  userId: string | null;
  source: 'id' | 'user_id' | 'missing';
  isValid: boolean;
}

/**
 * Gets comprehensive debug information about user ID extraction
 */
export function getUserIdDebugInfo(user: AuthUser | null | undefined): UserIdDebugInfo {
  const userId = extractUserId(user);
  const source = getUserIdSource(user);
  
  return {
    hasUser: !!user,
    userId,
    source,
    isValid: userId !== null,
  };
}