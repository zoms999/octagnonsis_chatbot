import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { 
  authReducer, 
  initialAuthState, 
  validateLoginCredentials,
  isValidJWT,
  SecureTokenManager,
  setupAutoLogout
} from '../auth';
import { AuthUser, LoginCredentials } from '../types';

describe('Authentication Utilities', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage
    const localStorageMock = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    };
    vi.stubGlobal('localStorage', localStorageMock);
    
    // Mock window
    vi.stubGlobal('window', {
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      __auth_token__: undefined,
      __refresh_token__: undefined,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('authReducer', () => {
    it('should handle AUTH_START action', () => {
      const action = { type: 'AUTH_START' as const };
      const newState = authReducer(initialAuthState, action);

      expect(newState.isLoading).toBe(true);
      expect(newState.error).toBeNull();
    });

    it('should handle AUTH_SUCCESS action', () => {
      const user: AuthUser = {
        id: '1',
        name: 'Test User',
        type: 'personal',
      };
      const action = { type: 'AUTH_SUCCESS' as const, payload: user };
      const newState = authReducer(initialAuthState, action);

      expect(newState.user).toEqual(user);
      expect(newState.isLoading).toBe(false);
      expect(newState.isAuthenticated).toBe(true);
      expect(newState.error).toBeNull();
    });

    it('should handle AUTH_ERROR action', () => {
      const errorMessage = 'Login failed';
      const action = { type: 'AUTH_ERROR' as const, payload: errorMessage };
      const newState = authReducer(initialAuthState, action);

      expect(newState.user).toBeNull();
      expect(newState.isLoading).toBe(false);
      expect(newState.isAuthenticated).toBe(false);
      expect(newState.error).toBe(errorMessage);
    });

    it('should handle AUTH_LOGOUT action', () => {
      const authenticatedState = {
        ...initialAuthState,
        user: { id: '1', name: 'Test User', type: 'personal' as const },
        isAuthenticated: true,
      };
      const action = { type: 'AUTH_LOGOUT' as const };
      const newState = authReducer(authenticatedState, action);

      expect(newState.user).toBeNull();
      expect(newState.isLoading).toBe(false);
      expect(newState.isAuthenticated).toBe(false);
      expect(newState.error).toBeNull();
    });

    it('should handle AUTH_CLEAR_ERROR action', () => {
      const errorState = {
        ...initialAuthState,
        error: 'Some error',
      };
      const action = { type: 'AUTH_CLEAR_ERROR' as const };
      const newState = authReducer(errorState, action);

      expect(newState.error).toBeNull();
    });
  });

  describe('validateLoginCredentials', () => {
    it('should return no errors for valid personal credentials', () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'password123',
        loginType: 'personal',
      };

      const errors = validateLoginCredentials(credentials);
      expect(errors).toHaveLength(0);
    });

    it('should return no errors for valid organization credentials', () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'password123',
        loginType: 'organization',
        sessionCode: 'ABC123',
      };

      const errors = validateLoginCredentials(credentials);
      expect(errors).toHaveLength(0);
    });

    it('should return error for missing username', () => {
      const credentials: LoginCredentials = {
        username: '',
        password: 'password123',
        loginType: 'personal',
      };

      const errors = validateLoginCredentials(credentials);
      expect(errors).toContain('Username is required');
    });

    it('should return error for missing password', () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: '',
        loginType: 'personal',
      };

      const errors = validateLoginCredentials(credentials);
      expect(errors).toContain('Password is required');
    });

    it('should return error for missing session code in organization login', () => {
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'password123',
        loginType: 'organization',
      };

      const errors = validateLoginCredentials(credentials);
      expect(errors).toContain('Session code is required for organization login');
    });

    it('should return multiple errors for invalid credentials', () => {
      const credentials: LoginCredentials = {
        username: '',
        password: '',
        loginType: 'organization',
      };

      const errors = validateLoginCredentials(credentials);
      expect(errors).toHaveLength(3);
      expect(errors).toContain('Username is required');
      expect(errors).toContain('Password is required');
      expect(errors).toContain('Session code is required for organization login');
    });
  });

  describe('isValidJWT', () => {
    it('should return false for invalid JWT format', () => {
      expect(isValidJWT('invalid-token')).toBe(false);
      expect(isValidJWT('invalid.token')).toBe(false);
      expect(isValidJWT('')).toBe(false);
    });

    it('should return false for expired token', () => {
      // Create a mock expired JWT (exp in the past)
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 3600 })); // 1 hour ago
      const signature = 'mock-signature';
      const expiredToken = `${header}.${payload}.${signature}`;

      expect(isValidJWT(expiredToken)).toBe(false);
    });

    it('should return true for valid token', () => {
      // Create a mock valid JWT (exp in the future)
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })); // 1 hour from now
      const signature = 'mock-signature';
      const validToken = `${header}.${payload}.${signature}`;

      expect(isValidJWT(validToken)).toBe(true);
    });
  });

  describe('SecureTokenManager', () => {
    beforeEach(() => {
      // Clear any existing tokens
      SecureTokenManager.clearTokens();
    });

    describe('setTokens and getTokens', () => {
      it('should store and retrieve access token from memory', () => {
        const accessToken = 'access-token-123';
        const refreshToken = 'refresh-token-456';
        
        SecureTokenManager.setTokens(accessToken, refreshToken);
        
        expect(SecureTokenManager.getAccessToken()).toBe(accessToken);
        expect(SecureTokenManager.getRefreshToken()).toBe(refreshToken);
      });

      it('should store tokens in localStorage as fallback', () => {
        const accessToken = 'access-token-123';
        const refreshToken = 'refresh-token-456';
        const expiresAt = '2024-12-31T23:59:59Z';
        
        SecureTokenManager.setTokens(accessToken, refreshToken, expiresAt);
        
        expect(localStorage.setItem).toHaveBeenCalledWith('access_token', accessToken);
        expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', refreshToken);
        expect(localStorage.setItem).toHaveBeenCalledWith('token_expires', expiresAt);
      });

      it('should fallback to localStorage when memory tokens are not available', () => {
        const accessToken = 'access-token-123';
        vi.mocked(localStorage.getItem).mockReturnValue(accessToken);
        
        expect(SecureTokenManager.getAccessToken()).toBe(accessToken);
        expect(localStorage.getItem).toHaveBeenCalledWith('access_token');
      });
    });

    describe('clearTokens', () => {
      it('should clear tokens from memory and localStorage', () => {
        SecureTokenManager.setTokens('access', 'refresh');
        SecureTokenManager.clearTokens();
        
        // After clearing, tokens should return null or undefined
        expect(SecureTokenManager.getAccessToken()).toBeFalsy();
        expect(SecureTokenManager.getRefreshToken()).toBeFalsy();
        expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
        expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token');
        expect(localStorage.removeItem).toHaveBeenCalledWith('token_expires');
      });
    });

    describe('isAuthenticated', () => {
      it('should return false when no token exists', () => {
        expect(SecureTokenManager.isAuthenticated()).toBe(false);
      });

      it('should return true when valid token exists', () => {
        SecureTokenManager.setTokens('valid-token', 'refresh-token');
        expect(SecureTokenManager.isAuthenticated()).toBe(true);
      });

      it('should return false and clear tokens when token is expired', () => {
        const expiredDate = new Date(Date.now() - 3600000).toISOString(); // 1 hour ago
        vi.mocked(localStorage.getItem).mockImplementation((key) => {
          if (key === 'token_expires') return expiredDate;
          if (key === 'access_token') return 'expired-token';
          return null;
        });
        
        expect(SecureTokenManager.isAuthenticated()).toBe(false);
        expect(localStorage.removeItem).toHaveBeenCalled();
      });
    });

    describe('isTokenExpired', () => {
      it('should return false when no expiration date exists', () => {
        expect(SecureTokenManager.isTokenExpired()).toBe(false);
      });

      it('should return true when token is expired', () => {
        const expiredDate = new Date(Date.now() - 3600000).toISOString();
        vi.mocked(localStorage.getItem).mockReturnValue(expiredDate);
        
        expect(SecureTokenManager.isTokenExpired()).toBe(true);
      });

      it('should return false when token is not expired', () => {
        const futureDate = new Date(Date.now() + 3600000).toISOString();
        vi.mocked(localStorage.getItem).mockReturnValue(futureDate);
        
        expect(SecureTokenManager.isTokenExpired()).toBe(false);
      });
    });
  });

  describe('setupAutoLogout', () => {
    it('should add event listener for auth:logout', () => {
      const logoutCallback = vi.fn();
      const cleanup = setupAutoLogout(logoutCallback);
      
      expect(window.addEventListener).toHaveBeenCalledWith('auth:logout', logoutCallback);
      
      if (cleanup) {
        cleanup();
        expect(window.removeEventListener).toHaveBeenCalledWith('auth:logout', logoutCallback);
      }
    });

    it('should return undefined in non-browser environment', () => {
      vi.stubGlobal('window', undefined);
      const logoutCallback = vi.fn();
      const cleanup = setupAutoLogout(logoutCallback);
      
      expect(cleanup).toBeUndefined();
    });
  });
});