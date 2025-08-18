import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { ProtectedRoute, withAuth } from '../protected-route';
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

// Test component
const TestComponent = () => <div>Protected Content</div>;

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    (useRouter as any).mockReturnValue({
      push: mockPush,
    });

    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: {
        pathname: '/chat',
      },
      writable: true,
    });
  });

  it('should render children when user is authenticated', () => {
    (useAuth as any).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('should show loading fallback when loading', () => {
    (useAuth as any).mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    render(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('should show custom fallback when provided and loading', () => {
    (useAuth as any).mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    render(
      <ProtectedRoute fallback={<div>Custom Loading</div>}>
        <TestComponent />
      </ProtectedRoute>
    );

    expect(screen.getByText('Custom Loading')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('should redirect to login when not authenticated', () => {
    (useAuth as any).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>
    );

    expect(mockPush).toHaveBeenCalledWith('/login?returnTo=%2Fchat');
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('should redirect to custom redirect URL when not authenticated', () => {
    (useAuth as any).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    render(
      <ProtectedRoute redirectTo="/custom-login">
        <TestComponent />
      </ProtectedRoute>
    );

    expect(mockPush).toHaveBeenCalledWith('/custom-login?returnTo=%2Fchat');
  });
});

describe('withAuth HOC', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    (useRouter as any).mockReturnValue({
      push: mockPush,
    });

    Object.defineProperty(window, 'location', {
      value: {
        pathname: '/profile',
      },
      writable: true,
    });
  });

  it('should wrap component with authentication', () => {
    (useAuth as any).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    const AuthenticatedComponent = withAuth(TestComponent);
    
    render(<AuthenticatedComponent />);

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('should redirect when not authenticated', () => {
    (useAuth as any).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    const AuthenticatedComponent = withAuth(TestComponent);
    
    render(<AuthenticatedComponent />);

    expect(mockPush).toHaveBeenCalledWith('/login?returnTo=%2Fprofile');
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('should use custom options', () => {
    (useAuth as any).mockReturnValue({
      isAuthenticated: false,
      isLoading: true,
    });

    const AuthenticatedComponent = withAuth(TestComponent, {
      fallback: <div>Custom HOC Loading</div>,
      redirectTo: '/custom-auth',
    });
    
    render(<AuthenticatedComponent />);

    expect(screen.getByText('Custom HOC Loading')).toBeInTheDocument();
  });

  it('should preserve component display name', () => {
    TestComponent.displayName = 'TestComponent';
    const AuthenticatedComponent = withAuth(TestComponent);
    
    expect(AuthenticatedComponent.displayName).toBe('withAuth(TestComponent)');
  });
});