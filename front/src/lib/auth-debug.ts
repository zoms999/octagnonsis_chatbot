// Authentication debug utilities to identify user state and token issues

import { AuthUser } from './types';
import { SecureTokenManager } from './auth';
import * as UserUtils from './user-utils';

export interface AuthDebugInfo {
  isAuthenticated: boolean;
  userId: string | null;
  userIdSource: 'id' | 'user_id' | 'missing';
  tokenExists: boolean;
  tokenValid: boolean;
  tokenExpired: boolean;
  userObject: any;
  tokenDetails: {
    accessToken: string | null;
    refreshToken: string | null;
    expiresAt: string | null;
  };
}

export class AuthDebugger {
  /**
   * Validates the current authentication state and returns detailed debug info
   */
  static validateAuthState(user: any): AuthDebugInfo {
    console.log('🔍 AuthDebugger: Starting auth state validation');
    console.log('🔍 AuthDebugger: Raw user object:', user);

    // Extract user ID from different possible sources
    const userId = this.extractUserId(user);
    const userIdSource = this.getUserIdSource(user);
    
    // Check token state
    const accessToken = SecureTokenManager.getAccessToken();
    const refreshToken = SecureTokenManager.getRefreshToken();
    const expiresAt = SecureTokenManager.getTokenExpiration();
    const tokenExists = !!accessToken;
    const tokenValid = tokenExists && this.isValidJWT(accessToken);
    const tokenExpired = SecureTokenManager.isTokenExpired();
    
    const debugInfo: AuthDebugInfo = {
      isAuthenticated: SecureTokenManager.isAuthenticated(),
      userId,
      userIdSource,
      tokenExists,
      tokenValid,
      tokenExpired,
      userObject: user,
      tokenDetails: {
        accessToken: accessToken ? `${accessToken.substring(0, 20)}...` : null,
        refreshToken: refreshToken ? `${refreshToken.substring(0, 20)}...` : null,
        expiresAt,
      },
    };

    console.log('🔍 AuthDebugger: Debug info generated:', debugInfo);
    return debugInfo;
  }

  /**
   * Logs comprehensive authentication state information to console
   */
  static logAuthState(user: any): void {
    console.group('🔍 AUTH DEBUG STATE');
    
    const debugInfo = this.validateAuthState(user);
    
    console.log('📊 Authentication Status:', debugInfo.isAuthenticated ? '✅ AUTHENTICATED' : '❌ NOT AUTHENTICATED');
    console.log('👤 User ID:', debugInfo.userId || '❌ MISSING');
    console.log('🔑 User ID Source:', debugInfo.userIdSource);
    console.log('🎫 Token Exists:', debugInfo.tokenExists ? '✅ YES' : '❌ NO');
    console.log('✅ Token Valid:', debugInfo.tokenValid ? '✅ YES' : '❌ NO');
    console.log('⏰ Token Expired:', debugInfo.tokenExpired ? '❌ YES' : '✅ NO');
    
    if (debugInfo.tokenDetails.expiresAt) {
      const expiryDate = new Date(debugInfo.tokenDetails.expiresAt);
      const now = new Date();
      const timeUntilExpiry = expiryDate.getTime() - now.getTime();
      console.log('⏱️ Token Expires:', expiryDate.toLocaleString());
      console.log('⏱️ Time Until Expiry:', timeUntilExpiry > 0 ? `${Math.round(timeUntilExpiry / 1000 / 60)} minutes` : 'EXPIRED');
    }
    
    console.log('🔍 Raw User Object:', debugInfo.userObject);
    console.log('🎫 Token Details:', debugInfo.tokenDetails);
    
    // Check for common issues
    const issues = this.identifyAuthIssues(debugInfo);
    if (issues.length > 0) {
      console.group('⚠️ IDENTIFIED ISSUES');
      issues.forEach((issue, index) => {
        console.log(`${index + 1}. ${issue}`);
      });
      console.groupEnd();
    }
    
    console.groupEnd();
  }

  /**
   * Extracts user ID from user object, handling different field names
   * @deprecated Use extractUserId from user-utils instead
   */
  static extractUserId(user: any): string | null {
    return UserUtils.extractUserId(user);
  }

  /**
   * Determines which field was used as the user ID source
   * @deprecated Use getUserIdSource from user-utils instead
   */
  private static getUserIdSource(user: any): 'id' | 'user_id' | 'missing' {
    return UserUtils.getUserIdSource(user);
  }

  /**
   * Validates JWT token format and expiration
   */
  private static isValidJWT(token: string | null): boolean {
    if (!token) return false;
    
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return false;

      // Decode payload to check expiration
      const payload = JSON.parse(atob(parts[1]));
      const now = Math.floor(Date.now() / 1000);
      
      return payload.exp > now;
    } catch {
      return false;
    }
  }

  /**
   * Identifies common authentication issues
   */
  private static identifyAuthIssues(debugInfo: AuthDebugInfo): string[] {
    const issues: string[] = [];
    
    if (!debugInfo.userId) {
      issues.push('User ID is missing from user object');
    }
    
    if (!debugInfo.tokenExists) {
      issues.push('No access token found in storage');
    }
    
    if (debugInfo.tokenExists && !debugInfo.tokenValid) {
      issues.push('Access token exists but is invalid or malformed');
    }
    
    if (debugInfo.tokenExpired) {
      issues.push('Access token has expired');
    }
    
    if (debugInfo.userIdSource === 'user_id') {
      issues.push('User ID found in legacy "user_id" field - may indicate backend compatibility issue');
    }
    
    if (debugInfo.isAuthenticated && !debugInfo.userId) {
      issues.push('System reports authenticated but no user ID available - critical issue');
    }
    
    if (!debugInfo.isAuthenticated && debugInfo.tokenExists && debugInfo.tokenValid) {
      issues.push('Valid token exists but system reports not authenticated - token validation issue');
    }
    
    return issues;
  }

  /**
   * Creates a test user object for debugging purposes
   */
  static createTestUser(userId: string = 'test-user-123'): AuthUser {
    return {
      id: userId,
      name: 'Test User',
      type: 'personal',
    };
  }

  /**
   * Simulates different user object scenarios for testing
   */
  static createTestScenarios(): Record<string, any> {
    return {
      validUser: {
        id: 'user-123',
        name: 'Valid User',
        type: 'personal',
      },
      legacyUser: {
        user_id: 'legacy-user-456',
        name: 'Legacy User',
        type: 'personal',
      },
      missingIdUser: {
        name: 'No ID User',
        type: 'personal',
      },
      nullUser: null,
      undefinedUser: undefined,
      emptyUser: {},
    };
  }

  /**
   * Runs a comprehensive auth debug test
   */
  static runDebugTest(user: any): void {
    console.group('🧪 AUTH DEBUG TEST');
    
    console.log('🔍 Testing current user state...');
    this.logAuthState(user);
    
    console.log('🧪 Testing various user scenarios...');
    const scenarios = this.createTestScenarios();
    
    Object.entries(scenarios).forEach(([scenarioName, testUser]) => {
      console.group(`📋 Scenario: ${scenarioName}`);
      const debugInfo = this.validateAuthState(testUser);
      console.log('Result:', debugInfo);
      console.groupEnd();
    });
    
    console.groupEnd();
  }
}

// Export convenience functions
export const logAuthState = AuthDebugger.logAuthState;
export const validateAuthState = AuthDebugger.validateAuthState;
export const extractUserId = AuthDebugger.extractUserId;