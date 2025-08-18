import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import { LoginForm } from '../login-form';
import { useAuth } from '@/providers/auth-provider';

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(),
}));

// Mock auth provider
vi.mock('@/providers/auth-provider', () => ({
  useAuth: vi.fn(),
}));

const mockPush = vi.fn();
const mockLogin = vi.fn();
const mockClearError = vi.fn();

const defaultAuthState = {
  login: mockLogin,
  isLoading: false,
  error: null,
  clearError: mockClearError,
  isAuthenticated: false,
};

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    (useRouter as any).mockReturnValue({
      push: mockPush,
    });

    (useAuth as any).mockReturnValue(defaultAuthState);
  });

  it('should render login form with personal tab selected by default', () => {
    render(<LoginForm />);

    expect(screen.getByRole('heading', { name: 'Sign In' })).toBeInTheDocument();
    expect(screen.getByText('Personal')).toBeInTheDocument();
    expect(screen.getByText('Organization')).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument();
  });

  it('should show session code field when organization tab is selected', async () => {
    render(<LoginForm />);

    const organizationTab = screen.getByText('Organization');
    fireEvent.click(organizationTab);

    await waitFor(() => {
      expect(screen.getByLabelText('Session Code')).toBeInTheDocument();
    });
  });

  it('should validate required fields and show errors', async () => {
    render(<LoginForm />);

    const submitButton = screen.getByRole('button', { name: 'Sign In' });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Username is required')).toBeInTheDocument();
      expect(screen.getByText('Password is required')).toBeInTheDocument();
    });

    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('should validate session code for organization login', async () => {
    render(<LoginForm />);

    // Switch to organization tab
    const organizationTab = screen.getByText('Organization');
    fireEvent.click(organizationTab);

    // Fill username and password but not session code
    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    const submitButton = screen.getByRole('button', { name: 'Sign In' });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Session code is required for organization login')).toBeInTheDocument();
    });

    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('should submit valid personal login credentials', async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValue(undefined);
    
    render(<LoginForm />);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    
    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'password123');

    const submitButton = screen.getByRole('button', { name: 'Sign In' });
    await user.click(submitButton);

    expect(mockLogin).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'password123',
      loginType: 'personal',
      sessionCode: undefined,
    });
  });

  it('should submit valid organization login credentials', async () => {
    mockLogin.mockResolvedValue(undefined);
    
    render(<LoginForm />);

    // Switch to organization tab
    const organizationTab = screen.getByText('Organization');
    fireEvent.click(organizationTab);

    await waitFor(() => {
      expect(screen.getByLabelText('Session Code')).toBeInTheDocument();
    });

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    const sessionCodeInput = screen.getByLabelText('Session Code');
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.change(sessionCodeInput, { target: { value: 'ABC123' } });

    const submitButton = screen.getByRole('button', { name: 'Sign In' });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
        loginType: 'organization',
        sessionCode: 'ABC123',
      });
    });
  });

  it('should display error message from auth provider', () => {
    (useAuth as any).mockReturnValue({
      login: mockLogin,
      isLoading: false,
      error: 'Invalid credentials. Please check your username and password.',
      clearError: mockClearError,
      isAuthenticated: false,
    });

    render(<LoginForm />);

    expect(screen.getByText('Invalid credentials. Please check your username and password.')).toBeInTheDocument();
  });

  it('should show loading state during submission', () => {
    (useAuth as any).mockReturnValue({
      login: mockLogin,
      isLoading: true,
      error: null,
      clearError: mockClearError,
      isAuthenticated: false,
    });

    render(<LoginForm />);

    expect(screen.getByText('Signing in...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled();
  });

  it('should redirect when authenticated', () => {
    (useAuth as any).mockReturnValue({
      login: mockLogin,
      isLoading: false,
      error: null,
      clearError: mockClearError,
      isAuthenticated: true,
    });

    render(<LoginForm />);

    expect(mockPush).toHaveBeenCalledWith('/chat');
  });

  it('should call onSuccess callback when provided and authenticated', () => {
    const mockOnSuccess = vi.fn();
    
    (useAuth as any).mockReturnValue({
      login: mockLogin,
      isLoading: false,
      error: null,
      clearError: mockClearError,
      isAuthenticated: true,
    });

    render(<LoginForm onSuccess={mockOnSuccess} />);

    expect(mockOnSuccess).toHaveBeenCalled();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('should clear errors when form data changes', async () => {
    (useAuth as any).mockReturnValue({
      login: mockLogin,
      isLoading: false,
      error: 'Some error',
      clearError: mockClearError,
      isAuthenticated: false,
    });

    render(<LoginForm />);

    const usernameInput = screen.getByLabelText('Username');
    fireEvent.change(usernameInput, { target: { value: 'test' } });

    await waitFor(() => {
      expect(mockClearError).toHaveBeenCalled();
    });
  });

  it('should handle Enter key press to submit form', async () => {
    mockLogin.mockResolvedValue(undefined);
    
    render(<LoginForm />);

    const usernameInput = screen.getByLabelText('Username');
    const passwordInput = screen.getByLabelText('Password');
    
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    fireEvent.keyDown(passwordInput, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
        loginType: 'personal',
        sessionCode: undefined,
      });
    });
  });
});