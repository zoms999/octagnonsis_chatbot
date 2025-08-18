'use client';

import { useEffect } from 'react';
import { useToast } from '@/providers/toast-provider';

/**
 * Global error handler component that listens for global error events
 * and displays appropriate toast notifications
 */
export const GlobalErrorHandler: React.FC = () => {
  const { showError, showSuccess, showWarning } = useToast();

  useEffect(() => {
    // Handle global errors from React Query and other sources
    const handleGlobalError = (event: CustomEvent) => {
      const { error, context } = event.detail;
      showError(error, context);
    };

    // Handle global success messages
    const handleGlobalSuccess = (event: CustomEvent) => {
      const { message, title } = event.detail;
      showSuccess(message, title);
    };

    // Handle global warnings
    const handleGlobalWarning = (event: CustomEvent) => {
      const { message, title } = event.detail;
      showWarning(message, title);
    };

    // Handle authentication logout events
    const handleAuthLogout = (event: CustomEvent) => {
      const { reason } = event.detail;
      
      if (reason === 'auth_error') {
        showWarning('Your session has expired. Please log in again.', 'Session Expired');
      } else if (reason === 'manual') {
        showSuccess('You have been logged out successfully.', 'Logged Out');
      }
    };

    // Handle rate limit events
    const handleRateLimit = (event: CustomEvent) => {
      const { retryAfter } = event.detail;
      showWarning(
        `Too many requests. Please wait ${retryAfter} seconds before trying again.`,
        'Rate Limited'
      );
    };

    // Add event listeners
    window.addEventListener('global:error', handleGlobalError as EventListener);
    window.addEventListener('global:success', handleGlobalSuccess as EventListener);
    window.addEventListener('global:warning', handleGlobalWarning as EventListener);
    window.addEventListener('auth:logout', handleAuthLogout as EventListener);
    window.addEventListener('rate_limit', handleRateLimit as EventListener);

    // Cleanup event listeners
    return () => {
      window.removeEventListener('global:error', handleGlobalError as EventListener);
      window.removeEventListener('global:success', handleGlobalSuccess as EventListener);
      window.removeEventListener('global:warning', handleGlobalWarning as EventListener);
      window.removeEventListener('auth:logout', handleAuthLogout as EventListener);
      window.removeEventListener('rate_limit', handleRateLimit as EventListener);
    };
  }, [showError, showSuccess, showWarning]);

  // This component doesn't render anything
  return null;
};

export default GlobalErrorHandler;