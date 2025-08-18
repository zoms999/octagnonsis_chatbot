'use client';

import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { AuthUser, LoginCredentials, LoginResponse } from '@/lib/types';
import { 
  SecureTokenManager, 
  AuthState, 
  AuthAction, 
  authReducer, 
  initialAuthState,
  validateLoginCredentials,
  setupAutoLogout
} from '@/lib/auth';
import { ApiClient, ApiErrorHandler } from '@/lib/api';

// Authentication context type
interface AuthContextType {
  // State
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;

  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  validateSession: () => Promise<void>;
  getToken: () => Promise<string>;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth provider props
interface AuthProviderProps {
  children: React.ReactNode;
}

// Auth provider component
export function AuthProvider({ children }: AuthProviderProps) {
  const [state, dispatch] = useReducer(authReducer, initialAuthState);

  // Login function
  const login = useCallback(async (credentials: LoginCredentials): Promise<void> => {
    // Validate credentials
    const validationErrors = validateLoginCredentials(credentials);
    if (validationErrors.length > 0) {
      dispatch({ type: 'AUTH_ERROR', payload: validationErrors.join(', ') });
      return;
    }

    dispatch({ type: 'AUTH_START' });

    try {
      console.log('AuthProvider: Calling ApiClient.login');
      const response: LoginResponse = await ApiClient.login(credentials);
      console.log('AuthProvider: Login response received:', response);
      
      // Check if login was successful and we have user data
      if (!response.success || !response.user) {
        console.error('AuthProvider: Login failed - invalid response:', response);
        throw new Error(response.message || 'Login failed - no user data received');
      }
      
      console.log('AuthProvider: Login successful, dispatching AUTH_SUCCESS');
      // Store tokens securely (tokens are already stored in ApiClient.login)
      // Just dispatch the success action with user data
      dispatch({ type: 'AUTH_SUCCESS', payload: response.user });
      console.log('AuthProvider: AUTH_SUCCESS dispatched');
      
      // Force a small delay to ensure all state updates are processed
      await new Promise(resolve => setTimeout(resolve, 50));
    } catch (error: any) {
      let errorMessage = 'Login failed. Please try again.';

      if (ApiErrorHandler.isAuthError(error)) {
        errorMessage = 'Invalid credentials. Please check your username and password.';
      } else if (ApiErrorHandler.isValidationError(error)) {
        errorMessage = error.message || 'Please check your input and try again.';
      } else if (ApiErrorHandler.isNetworkError(error)) {
        errorMessage = 'Network error. Please check your connection and try again.';
      } else if (ApiErrorHandler.isServerError(error)) {
        errorMessage = 'Server error. Please try again later.';
      }

      dispatch({ type: 'AUTH_ERROR', payload: errorMessage });
    }
  }, []);

  // Logout function
  const logout = useCallback(async (): Promise<void> => {
    try {
      // Call logout API to invalidate server-side session
      await ApiClient.logout();
    } catch (error) {
      // Continue with logout even if API call fails
      console.warn('Logout API call failed:', error);
    } finally {
      // Always clear local tokens and state
      SecureTokenManager.clearTokens();
      dispatch({ type: 'AUTH_LOGOUT' });
    }
  }, []);

  // Validate session function
  const validateSession = useCallback(async (): Promise<void> => {
    if (!SecureTokenManager.isAuthenticated()) {
      dispatch({ type: 'AUTH_LOGOUT' });
      return;
    }

    dispatch({ type: 'AUTH_START' });

    try {
      const user = await ApiClient.validateSession();
      dispatch({ type: 'AUTH_SUCCESS', payload: user });
    } catch (error: any) {
      // If session validation fails, clear tokens and logout
      SecureTokenManager.clearTokens();
      dispatch({ type: 'AUTH_LOGOUT' });
    }
  }, []);

  // Clear error function
  const clearError = useCallback((): void => {
    dispatch({ type: 'AUTH_CLEAR_ERROR' });
  }, []);

  // Get token function
  const getToken = useCallback(async (): Promise<string> => {
    const token = SecureTokenManager.getAccessToken();
    if (!token) {
      throw new Error('No access token available');
    }
    return token;
  }, []);

  // Auto-logout handler for 401 responses
  const handleAutoLogout = useCallback((): void => {
    SecureTokenManager.clearTokens();
    dispatch({ type: 'AUTH_LOGOUT' });
  }, []);

  // Initialize authentication state on mount
  useEffect(() => {
    let mounted = true;

    const initializeAuth = async () => {
      // Set up auto-logout listener
      const cleanup = setupAutoLogout(handleAutoLogout);

      // Check if user is already authenticated
      if (SecureTokenManager.isAuthenticated()) {
        try {
          await validateSession();
        } catch (error) {
          // Session validation failed, user will be logged out
          console.warn('Session validation failed during initialization:', error);
        }
      } else {
        // No valid token found, set to unauthenticated state
        if (mounted) {
          dispatch({ type: 'AUTH_LOGOUT' });
        }
      }

      return cleanup;
    };

    initializeAuth();

    return () => {
      mounted = false;
    };
  }, [validateSession, handleAutoLogout]);

  // Context value
  const contextValue: AuthContextType = {
    // State
    user: state.user,
    isLoading: state.isLoading,
    isAuthenticated: state.isAuthenticated,
    error: state.error,

    // Actions
    login,
    logout,
    clearError,
    validateSession,
    getToken,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth context
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  return context;
}

// Individual hooks for specific auth actions
export function useLogin() {
  const { login, isLoading, error } = useAuth();
  return { login, isLoading, error };
}

export function useLogout() {
  const { logout } = useAuth();
  return logout;
}

// Hook for auth state
export function useAuthState() {
  const { user, isLoading, isAuthenticated, error } = useAuth();
  return { user, isLoading, isAuthenticated, error };
}