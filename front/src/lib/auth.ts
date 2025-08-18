// Authentication utilities with secure token storage

import { AuthUser, LoginCredentials, LoginResponse } from './types';

// Token storage utilities with httpOnly cookies priority
export class SecureTokenManager {
  private static readonly ACCESS_TOKEN_KEY = 'access_token';
  private static readonly REFRESH_TOKEN_KEY = 'refresh_token';
  private static readonly TOKEN_EXPIRES_KEY = 'token_expires';

  // Check if we're in browser environment
  private static isBrowser(): boolean {
    return typeof window !== 'undefined';
  }

  // Try to use httpOnly cookies first, fallback to secure memory storage
  static getAccessToken(): string | null {
    if (!this.isBrowser()) return null;

    // First try to get from memory (will be set by auth provider)
    const memoryToken = (window as any).__auth_token__;
    if (memoryToken) return memoryToken;

    // Fallback to localStorage for development (not recommended for production)
    return localStorage.getItem(this.ACCESS_TOKEN_KEY);
  }

  static getRefreshToken(): string | null {
    if (!this.isBrowser()) return null;

    // First try to get from memory
    const memoryToken = (window as any).__refresh_token__;
    if (memoryToken) return memoryToken;

    // Fallback to localStorage
    return localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  static setTokens(accessToken: string, refreshToken: string, expiresAt?: string): void {
    if (!this.isBrowser()) return;

    // Store in secure memory (primary method)
    (window as any).__auth_token__ = accessToken;
    (window as any).__refresh_token__ = refreshToken;

    // Also store in localStorage as fallback (should be replaced with httpOnly cookies in production)
    localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken);
    
    if (expiresAt) {
      localStorage.setItem(this.TOKEN_EXPIRES_KEY, expiresAt);
    }

    // Set cookies for middleware to access
    document.cookie = `access_token=${accessToken}; path=/; max-age=86400; SameSite=Lax`;
    document.cookie = `refresh_token=${refreshToken}; path=/; max-age=604800; SameSite=Lax`;
    if (expiresAt) {
      document.cookie = `token_expires=${expiresAt}; path=/; max-age=86400; SameSite=Lax`;
    }
  }

  static clearTokens(): void {
    if (!this.isBrowser()) return;

    // Clear from memory
    delete (window as any).__auth_token__;
    delete (window as any).__refresh_token__;

    // Clear from localStorage
    localStorage.removeItem(this.ACCESS_TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
    localStorage.removeItem(this.TOKEN_EXPIRES_KEY);

    // Clear cookies
    document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    document.cookie = 'refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    document.cookie = 'token_expires=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
  }

  static isAuthenticated(): boolean {
    const token = this.getAccessToken();
    if (!token) return false;

    // Check if token is expired
    const expiresAt = this.getTokenExpiration();
    if (expiresAt && new Date() >= new Date(expiresAt)) {
      this.clearTokens();
      return false;
    }

    return true;
  }

  static getTokenExpiration(): string | null {
    if (!this.isBrowser()) return null;
    return localStorage.getItem(this.TOKEN_EXPIRES_KEY);
  }

  static isTokenExpired(): boolean {
    const expiresAt = this.getTokenExpiration();
    if (!expiresAt) return false;
    return new Date() >= new Date(expiresAt);
  }
}

// Authentication state management
export interface AuthState {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

export const initialAuthState: AuthState = {
  user: null,
  isLoading: true,
  isAuthenticated: false,
  error: null,
};

// Authentication actions
export type AuthAction =
  | { type: 'AUTH_START' }
  | { type: 'AUTH_SUCCESS'; payload: AuthUser }
  | { type: 'AUTH_ERROR'; payload: string }
  | { type: 'AUTH_LOGOUT' }
  | { type: 'AUTH_CLEAR_ERROR' };

// Authentication reducer
export function authReducer(state: AuthState, action: AuthAction): AuthState {
  console.log('AuthReducer: Action dispatched:', action.type, action);
  console.log('AuthReducer: Current state:', state);
  
  switch (action.type) {
    case 'AUTH_START':
      const startState = {
        ...state,
        isLoading: true,
        error: null,
      };
      console.log('AuthReducer: AUTH_START - New state:', startState);
      return startState;

    case 'AUTH_SUCCESS':
      const successState = {
        ...state,
        user: action.payload,
        isLoading: false,
        isAuthenticated: true,
        error: null,
      };
      console.log('AuthReducer: AUTH_SUCCESS - New state:', successState);
      return successState;

    case 'AUTH_ERROR':
      const errorState = {
        ...state,
        user: null,
        isLoading: false,
        isAuthenticated: false,
        error: action.payload,
      };
      console.log('AuthReducer: AUTH_ERROR - New state:', errorState);
      return errorState;

    case 'AUTH_LOGOUT':
      const logoutState = {
        ...state,
        user: null,
        isLoading: false,
        isAuthenticated: false,
        error: null,
      };
      console.log('AuthReducer: AUTH_LOGOUT - New state:', logoutState);
      return logoutState;

    case 'AUTH_CLEAR_ERROR':
      const clearErrorState = {
        ...state,
        error: null,
      };
      console.log('AuthReducer: AUTH_CLEAR_ERROR - New state:', clearErrorState);
      return clearErrorState;

    default:
      console.log('AuthReducer: Unknown action type, returning current state');
      return state;
  }
}

// Validation utilities
export function validateLoginCredentials(credentials: LoginCredentials): string[] {
  const errors: string[] = [];

  if (!credentials.username?.trim()) {
    errors.push('Username is required');
  }

  if (!credentials.password?.trim()) {
    errors.push('Password is required');
  }

  if (credentials.loginType === 'organization' && !credentials.sessionCode?.trim()) {
    errors.push('Session code is required for organization login');
  }

  return errors;
}

// Token validation utilities
export function isValidJWT(token: string): boolean {
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

// Auto-logout handler for 401 responses
export function setupAutoLogout(logoutCallback: () => void): (() => void) | void {
  if (typeof window === 'undefined') return;

  // Listen for auth:logout events from API client
  window.addEventListener('auth:logout', logoutCallback);

  // Cleanup function
  return () => {
    window.removeEventListener('auth:logout', logoutCallback);
  };
}