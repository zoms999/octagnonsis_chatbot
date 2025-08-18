import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth, useLogin, useLogout, useAuthState } from '../auth-provider';
import { LoginCredentials, AuthUser, LoginResponse } from '@/lib/types';

// Mock dependencies
vi.mock('@/lib/api', () => ({
  ApiClient: {
    login: vi.fn(),
    logout: vi.fn(),
    validateSession: vi.fn(),
  },
  ApiErrorHandler: {
    isAuthError: vi.fn(),
    isValidationError: vi.fn(),
    isNetworkError: vi.fn(),
    isServerError: vi.fn(),
  },
}));

vi.mock('@/lib/auth', () => ({
  SecureTokenManager: {
    getAccessToken: vi.fn(),
    getRefreshToken: vi.fn(),
    setTokens: vi.fn(),
    clearTokens: vi.fn(),
    isAuthenticated: vi.fn(),
  },
  validateLoginCredentials: vi.fn(() => []),
  setupAutoLogout: vi.fn(() => vi.fn()),
  authReducer: (state: any, action: any) => {
    switch (action.type) {
      case 'AUTH_START':
        return { ...state, isLoading: true, error: null };
      case 'AUTH_SUCCESS':
        return { ...state, user: action.payload, isLoading: false, isAuthenticated: true, error: null };
      case 'AUTH_ERROR':
        return { ...state, user: null, isLoading: false, isAuthenticated: false, error: action.payload };
      case 'AUTH_LOGOUT':
        return { ...state, user: null, isLoading: false, isAuthenticated: false, error: null };
      case 'AUTH_CLEAR_ERROR':
        return { ...state, error: null };
      default:
        return state;
    }
  },
  initialAuthState: {
    user: null,
    isLoading: true,
    isAuthenticated: false,
    error: null,
  },
}));

// Test component to use hooks
function TestComponent() {
  const auth = useAuth();
  const { login } = useLogin();
  const logout = useLogout();
  const { user, isLoading, isAuthenticated, error } = useAuthState();

  return (
    <div>
      <div data-testid="user">{user?.name || 'No user'}</div>
      <div data-testid="loading">{isLoading ? 'Loading' : 'Not loading'}</div>
      <div data-testid="authenticated">{isAuthenticated ? 'Authenticated' : 'Not authenticated'}</div>
      <div data-testid="error">{error || 'No error'}</div>
      <button onClick={() => login({ username: 'test', password: 'test', loginType: 'personal' })}>
        Login
      </button>
      <button onClick={logout}>Logout</button>
      <button onClick={() => auth.validateSession()}>Validate</button>
      <button onClick={() => auth.clearError()}>Clear Error</button>
    </div>
  );
}

describe('AuthProvider', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    
    // Mock window for event handling
    vi.stubGlobal('window', {
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });

    // Get mocked modules
    const { SecureTokenManager } = await import('@/lib/auth');
    const { ApiClient } = await import('@/lib/api');

    // Default mock implementations
    vi.mocked(SecureTokenManager.isAuthenticated).mockReturnValue(false);
    vi.mocked(SecureTokenManager.getAccessToken).mockReturnValue(null);
    vi.mocked(ApiClient.login).mockClear();
    vi.mocked(ApiClient.logout).mockClear();
    vi.mocked(ApiClient.validateSession).mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('Provider initialization', () => {
    it('should provide auth context to children', () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      expect(screen.getByTestId('user')).toHaveTextContent('No user');
      expect(screen.getByTestId('loading')).toHaveTextContent('Loading');
      expect(screen.getByTestId('authenticated')).toHaveTextContent('Not authenticated');
    });

    it('should validate existing session on mount when authenticated', async () => {
      const mockUser: AuthUser = {
        id: '1',
        name: 'Test User',
        type: 'personal',
      };

      vi.mocked(SecureTokenManager.isAuthenticated).mockReturnValue(true);
      vi.mocked(ApiClient.validateSession).mockResolvedValue(mockUser);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(ApiClient.validateSession).toHaveBeenCalled();
      });
    });

    it('should set unauthenticated state when no valid token exists', async () => {
      vi.mocked(SecureTokenManager.isAuthenticated).mockReturnValue(false);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toHaveTextContent('Not authenticated');
        expect(screen.getByTestId('loading')).toHaveTextContent('Not loading');
      });
    });
  });

  describe('Login functionality', () => {
    it('should handle successful login', async () => {
      const mockUser: AuthUser = {
        id: '1',
        name: 'Test User',
        type: 'personal',
      };

      const mockLoginResponse: LoginResponse = {
        user: mockUser,
        tokens: {
          access: 'access-token',
          refresh: 'refresh-token',
        },
        expires_at: '2024-12-31T23:59:59Z',
      };

      vi.mocked(ApiClient.login).mockResolvedValue(mockLoginResponse);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const loginButton = screen.getByText('Login');
      
      await act(async () => {
        loginButton.click();
      });

      await waitFor(() => {
        expect(ApiClient.login).toHaveBeenCalledWith({
          username: 'test',
          password: 'test',
          loginType: 'personal',
        });
        expect(SecureTokenManager.setTokens).toHaveBeenCalledWith(
          'access-token',
          'refresh-token',
          '2024-12-31T23:59:59Z'
        );
      });
    });

    it('should handle login validation errors', async () => {
      const { validateLoginCredentials } = await import('@/lib/auth');
      vi.mocked(validateLoginCredentials).mockReturnValue(['Username is required']);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const loginButton = screen.getByText('Login');
      
      await act(async () => {
        loginButton.click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Username is required');
        expect(ApiClient.login).not.toHaveBeenCalled();
      });
    });

    it('should handle API login errors', async () => {
      const mockError = {
        message: 'Invalid credentials',
        status: 401,
        type: 'auth_error',
      };

      vi.mocked(ApiClient.login).mockRejectedValue(mockError);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const loginButton = screen.getByText('Login');
      
      await act(async () => {
        loginButton.click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Invalid credentials. Please check your username and password.');
      });
    });

    it('should handle network errors during login', async () => {
      const { ApiErrorHandler } = await import('@/lib/api');
      vi.mocked(ApiErrorHandler.isNetworkError).mockReturnValue(true);
      
      const networkError = new TypeError('Failed to fetch');
      vi.mocked(ApiClient.login).mockRejectedValue(networkError);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const loginButton = screen.getByText('Login');
      
      await act(async () => {
        loginButton.click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('Network error. Please check your connection and try again.');
      });
    });
  });

  describe('Logout functionality', () => {
    it('should handle successful logout', async () => {
      vi.mocked(ApiClient.logout).mockResolvedValue();

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const logoutButton = screen.getByText('Logout');
      
      await act(async () => {
        logoutButton.click();
      });

      await waitFor(() => {
        expect(ApiClient.logout).toHaveBeenCalled();
        expect(SecureTokenManager.clearTokens).toHaveBeenCalled();
        expect(screen.getByTestId('authenticated')).toHaveTextContent('Not authenticated');
      });
    });

    it('should clear tokens even if logout API fails', async () => {
      vi.mocked(ApiClient.logout).mockRejectedValue(new Error('API Error'));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const logoutButton = screen.getByText('Logout');
      
      await act(async () => {
        logoutButton.click();
      });

      await waitFor(() => {
        expect(SecureTokenManager.clearTokens).toHaveBeenCalled();
        expect(screen.getByTestId('authenticated')).toHaveTextContent('Not authenticated');
      });
    });
  });

  describe('Session validation', () => {
    it('should validate session successfully', async () => {
      const mockUser: AuthUser = {
        id: '1',
        name: 'Test User',
        type: 'personal',
      };

      vi.mocked(SecureTokenManager.isAuthenticated).mockReturnValue(true);
      vi.mocked(ApiClient.validateSession).mockResolvedValue(mockUser);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const validateButton = screen.getByText('Validate');
      
      await act(async () => {
        validateButton.click();
      });

      await waitFor(() => {
        expect(ApiClient.validateSession).toHaveBeenCalled();
        expect(screen.getByTestId('user')).toHaveTextContent('Test User');
        expect(screen.getByTestId('authenticated')).toHaveTextContent('Authenticated');
      });
    });

    it('should handle session validation failure', async () => {
      vi.mocked(SecureTokenManager.isAuthenticated).mockReturnValue(true);
      vi.mocked(ApiClient.validateSession).mockRejectedValue(new Error('Session expired'));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const validateButton = screen.getByText('Validate');
      
      await act(async () => {
        validateButton.click();
      });

      await waitFor(() => {
        expect(SecureTokenManager.clearTokens).toHaveBeenCalled();
        expect(screen.getByTestId('authenticated')).toHaveTextContent('Not authenticated');
      });
    });

    it('should logout immediately if not authenticated', async () => {
      vi.mocked(SecureTokenManager.isAuthenticated).mockReturnValue(false);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const validateButton = screen.getByText('Validate');
      
      await act(async () => {
        validateButton.click();
      });

      await waitFor(() => {
        expect(ApiClient.validateSession).not.toHaveBeenCalled();
        expect(screen.getByTestId('authenticated')).toHaveTextContent('Not authenticated');
      });
    });
  });

  describe('Error handling', () => {
    it('should clear errors', async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // First cause an error
      vi.mocked(ApiClient.login).mockRejectedValue({ message: 'Test error', status: 400 });
      
      const loginButton = screen.getByText('Login');
      await act(async () => {
        loginButton.click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('error')).not.toHaveTextContent('No error');
      });

      // Then clear the error
      const clearButton = screen.getByText('Clear Error');
      await act(async () => {
        clearButton.click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('error')).toHaveTextContent('No error');
      });
    });
  });

  describe('Token management', () => {
    it('should get token when available', async () => {
      vi.mocked(SecureTokenManager.getAccessToken).mockReturnValue('test-token');

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const auth = useAuth();
      const token = await auth.getToken();
      
      expect(token).toBe('test-token');
    });

    it('should throw error when no token available', async () => {
      vi.mocked(SecureTokenManager.getAccessToken).mockReturnValue(null);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      const auth = useAuth();
      
      await expect(auth.getToken()).rejects.toThrow('No access token available');
    });
  });

  describe('Hook usage outside provider', () => {
    it('should throw error when useAuth is used outside provider', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      expect(() => {
        render(<TestComponent />);
      }).toThrow('useAuth must be used within an AuthProvider');
      
      consoleSpy.mockRestore();
    });
  });
});