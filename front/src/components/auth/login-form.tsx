'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/providers/auth-provider';
import { LoginCredentials } from '@/lib/types';
import { validateLoginCredentials } from '@/lib/auth';

interface LoginFormProps {
  onSuccess?: () => void;
  redirectTo?: string;
}

interface FormErrors {
  username?: string;
  password?: string;
  sessionCode?: string;
  general?: string;
}

export function LoginForm({ onSuccess, redirectTo = '/chat' }: LoginFormProps) {
  // Check for returnTo parameter in URL (client-side only)
  const [returnTo, setReturnTo] = useState(redirectTo);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const searchParams = new URLSearchParams(window.location.search);
      const urlReturnTo = searchParams.get('returnTo');
      if (urlReturnTo) {
        setReturnTo(urlReturnTo);
      }
    }
  }, []);
  const router = useRouter();
  const { login, isLoading, error, clearError, isAuthenticated } = useAuth();

  // Form state
  const [loginType, setLoginType] = useState<'personal' | 'organization'>('personal');
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    sessionCode: '',
  });
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    console.log('Auth state changed:', { isAuthenticated, isLoading, error });
    if (isAuthenticated && !isLoading) {
      console.log('User is authenticated, redirecting...');
      if (onSuccess) {
        console.log('Calling onSuccess callback');
        onSuccess();
      } else {
        console.log('Redirecting to:', returnTo);
        // Use window.location.href for more reliable redirect
        // This ensures the page fully reloads and middleware can properly validate the new auth state
        window.location.href = returnTo;
      }
    }
  }, [isAuthenticated, isLoading, error, returnTo, onSuccess]);

  // Clear auth provider errors when form data changes
  useEffect(() => {
    if (error) {
      clearError();
    }
  }, [formData, loginType, error, clearError]);

  // Handle input changes
  const handleInputChange = (field: keyof typeof formData) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    setFormData(prev => ({
      ...prev,
      [field]: e.target.value,
    }));

    // Clear specific field error when user starts typing
    if (formErrors[field as keyof FormErrors]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: undefined,
      }));
    }
  };

  // Handle login type change
  const handleLoginTypeChange = (value: string) => {
    setLoginType(value as 'personal' | 'organization');
    // Clear session code when switching to personal
    if (value === 'personal') {
      setFormData(prev => ({ ...prev, sessionCode: '' }));
    }
  };

  // Validate form
  const validateForm = (): boolean => {
    const errors: FormErrors = {};

    console.log('Validating form with data:', formData, 'loginType:', loginType);

    // Validate username
    if (!formData.username.trim()) {
      errors.username = 'Username is required';
    }

    // Validate password
    if (!formData.password.trim()) {
      errors.password = 'Password is required';
    }

    // Validate session code for organization login
    if (loginType === 'organization' && !formData.sessionCode.trim()) {
      errors.sessionCode = 'Session code is required for organization login';
    }

    console.log('Validation errors:', errors);
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    console.log('handleSubmit called with formData:', formData);

    if (isSubmitting || isLoading) {
      console.log('Skipping submit - already submitting or loading');
      return;
    }

    // Validate form locally first
    const isValid = validateForm();
    console.log('Validation result:', isValid, 'Current errors after validation:', formErrors);

    if (!isValid) {
      console.log('Form validation failed, stopping submission');
      return;
    }

    setIsSubmitting(true);

    try {
      const credentials: LoginCredentials = {
        username: formData.username.trim(),
        password: formData.password,
        loginType,
        sessionCode: loginType === 'organization' ? formData.sessionCode.trim() : undefined,
      };

      console.log('Calling login with credentials:', credentials);
      await login(credentials);
      console.log('Login call completed successfully');

      // Success will be handled by the useEffect that watches isAuthenticated
    } catch (err) {
      // Error will be handled by the auth provider and displayed via the error prop
      console.error('Login failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Enter key press
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isSubmitting && !isLoading) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto space-y-6" data-testid="login-form">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Sign In</h1>
        <p className="text-muted-foreground">
          Enter your credentials to access your aptitude analysis
        </p>
      </div>

      <Tabs value={loginType} onValueChange={handleLoginTypeChange}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="personal" data-testid="login-type-personal">Personal</TabsTrigger>
          <TabsTrigger value="organization" data-testid="login-type-organization">Organization</TabsTrigger>
        </TabsList>

        <form onSubmit={handleSubmit} className="space-y-4 mt-6">
          {/* General error message */}
          {error && (
            <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md" data-testid="login-error">
              {error}
            </div>
          )}

          {/* Username field */}
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              type="text"
              placeholder="Enter your username"
              value={formData.username}
              onChange={handleInputChange('username')}
              onKeyDown={handleKeyDown}
              error={formErrors.username}
              disabled={isSubmitting || isLoading}
              autoComplete="username"
              data-testid="username-input"
            />
            {formErrors.username && (
              <div className="text-sm text-destructive" data-testid="username-error">
                {formErrors.username}
              </div>
            )}
          </div>

          {/* Password field */}
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={formData.password}
              onChange={handleInputChange('password')}
              onKeyDown={handleKeyDown}
              error={formErrors.password}
              disabled={isSubmitting || isLoading}
              autoComplete="current-password"
              data-testid="password-input"
            />
            {formErrors.password && (
              <div className="text-sm text-destructive" data-testid="password-error">
                {formErrors.password}
              </div>
            )}
          </div>

          {/* Session code field for organization login */}
          {loginType === 'organization' && (
            <div className="space-y-2">
              <Label htmlFor="sessionCode">Session Code</Label>
              <Input
                id="sessionCode"
                type="text"
                placeholder="Enter organization session code"
                value={formData.sessionCode}
                onChange={handleInputChange('sessionCode')}
                onKeyDown={handleKeyDown}
                error={formErrors.sessionCode}
                disabled={isSubmitting || isLoading}
                autoComplete="off"
                data-testid="session-code-input"
              />
              {formErrors.sessionCode && (
                <div className="text-sm text-destructive" data-testid="session-code-error">
                  {formErrors.sessionCode}
                </div>
              )}
            </div>
          )}

          {/* Submit button */}
          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting || isLoading}
            data-testid="login-submit"
          >
            {isSubmitting || isLoading ? (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                <span>Signing in...</span>
              </div>
            ) : (
              'Sign In'
            )}
          </Button>
        </form>
      </Tabs>

      {/* Additional help text */}
      <div className="text-center text-sm text-muted-foreground">
        {loginType === 'personal' && (
          <p>Use your personal account credentials to access your individual aptitude analysis.</p>
        )}
        {loginType === 'organization' && (
          <p>Use your organization credentials and session code provided by your administrator.</p>
        )}
      </div>

      {/* Debug: Show current auth state */}
      <div className="text-center text-xs text-muted-foreground border-t pt-4">
        <p>Debug: isAuthenticated={isAuthenticated.toString()}, isLoading={isLoading.toString()}</p>
        {isAuthenticated && (
          <button
            onClick={() => {
              console.log('Manual logout triggered');
              // Get logout function from useAuth
              const { logout } = useAuth();
              logout();
            }}
            className="mt-2 text-xs underline text-red-500"
          >
            Force Logout (Debug)
          </button>
        )}
      </div>
    </div>
  );
}