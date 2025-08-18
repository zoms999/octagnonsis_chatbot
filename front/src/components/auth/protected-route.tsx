'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/providers/auth-provider';

interface ProtectedRouteProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  redirectTo?: string;
}

export function ProtectedRoute({ 
  children, 
  fallback = <div>Loading...</div>,
  redirectTo = '/login'
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  console.log('ProtectedRoute: Auth state:', { isAuthenticated, isLoading });

  useEffect(() => {
    console.log('ProtectedRoute: useEffect triggered:', { isAuthenticated, isLoading });
    if (!isLoading && !isAuthenticated) {
      console.log('ProtectedRoute: User not authenticated, redirecting to login');
      // Get current path to redirect back after login
      const currentPath = window.location.pathname;
      const loginUrl = `${redirectTo}?returnTo=${encodeURIComponent(currentPath)}`;
      router.push(loginUrl);
    }
  }, [isAuthenticated, isLoading, router, redirectTo]);

  // Show loading state while checking authentication
  if (isLoading) {
    console.log('ProtectedRoute: Showing loading fallback (isLoading=true)');
    return <>{fallback}</>;
  }

  // Show loading state while redirecting
  if (!isAuthenticated) {
    console.log('ProtectedRoute: Showing loading fallback (not authenticated)');
    return <>{fallback}</>;
  }

  // User is authenticated, render children
  console.log('ProtectedRoute: User authenticated, rendering children');
  return <>{children}</>;
}

// Higher-order component version
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: {
    fallback?: React.ReactNode;
    redirectTo?: string;
  }
) {
  const AuthenticatedComponent = (props: P) => {
    return (
      <ProtectedRoute 
        fallback={options?.fallback}
        redirectTo={options?.redirectTo}
      >
        <Component {...props} />
      </ProtectedRoute>
    );
  };

  AuthenticatedComponent.displayName = `withAuth(${Component.displayName || Component.name})`;
  
  return AuthenticatedComponent;
}