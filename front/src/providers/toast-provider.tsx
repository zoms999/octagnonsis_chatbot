'use client';

import React, { createContext, useContext, useReducer, useCallback } from 'react';
import { ToastContainer } from '@/components/ui/toast';
import { ErrorNotificationFactory, ToastNotification } from '@/lib/error-handling';
import GlobalErrorHandler from '@/components/error/global-error-handler';

interface ToastContextType {
  addToast: (toast: Omit<ToastNotification, 'id'>) => void;
  removeToast: (id: string) => void;
  showError: (error: unknown, context?: string) => void;
  showSuccess: (message: string, title?: string) => void;
  showWarning: (message: string, title?: string) => void;
  showInfo: (message: string, title?: string) => void;
  clearAll: () => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

interface ToastState {
  toasts: ToastNotification[];
}

type ToastAction =
  | { type: 'ADD_TOAST'; toast: ToastNotification }
  | { type: 'REMOVE_TOAST'; id: string }
  | { type: 'CLEAR_ALL' };

const toastReducer = (state: ToastState, action: ToastAction): ToastState => {
  switch (action.type) {
    case 'ADD_TOAST':
      return {
        ...state,
        toasts: [...state.toasts, action.toast],
      };
    case 'REMOVE_TOAST':
      return {
        ...state,
        toasts: state.toasts.filter((toast) => toast.id !== action.id),
      };
    case 'CLEAR_ALL':
      return {
        ...state,
        toasts: [],
      };
    default:
      return state;
  }
};

interface ToastProviderProps {
  children: React.ReactNode;
  maxToasts?: number;
}

export const ToastProvider: React.FC<ToastProviderProps> = ({ 
  children, 
  maxToasts = 5 
}) => {
  const [state, dispatch] = useReducer(toastReducer, { toasts: [] });

  const addToast = useCallback((toast: Omit<ToastNotification, 'id'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    const newToast: ToastNotification = { ...toast, id };
    
    dispatch({ type: 'ADD_TOAST', toast: newToast });

    // Remove oldest toast if we exceed max limit
    if (state.toasts.length >= maxToasts) {
      const oldestToast = state.toasts[0];
      setTimeout(() => {
        dispatch({ type: 'REMOVE_TOAST', id: oldestToast.id });
      }, 100);
    }
  }, [state.toasts.length, maxToasts]);

  const removeToast = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_TOAST', id });
  }, []);

  const showError = useCallback((error: unknown, context?: string) => {
    const errorNotification = ErrorNotificationFactory.createErrorNotification(error, context);
    addToast(errorNotification);
  }, [addToast]);

  const showSuccess = useCallback((message: string, title = 'Success') => {
    const notification = ErrorNotificationFactory.createSuccessNotification(message, title);
    addToast(notification);
  }, [addToast]);

  const showWarning = useCallback((message: string, title = 'Warning') => {
    const notification = ErrorNotificationFactory.createWarningNotification(message, title);
    addToast(notification);
  }, [addToast]);

  const showInfo = useCallback((message: string, title = 'Info') => {
    const notification = ErrorNotificationFactory.createInfoNotification(message, title);
    addToast(notification);
  }, [addToast]);

  const clearAll = useCallback(() => {
    dispatch({ type: 'CLEAR_ALL' });
  }, []);

  const contextValue: ToastContextType = {
    addToast,
    removeToast,
    showError,
    showSuccess,
    showWarning,
    showInfo,
    clearAll,
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <GlobalErrorHandler />
      <ToastContainer 
        toasts={state.toasts.map(toast => ({
          id: toast.id,
          title: toast.title,
          description: toast.message,
          type: toast.type === 'error' ? 'error' : 
                toast.type === 'warning' ? 'warning' : 
                toast.type === 'info' ? 'default' : 'success',
          duration: toast.duration,
          onClose: removeToast,
        }))} 
        onClose={removeToast} 
      />
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

// Global error handler hook that integrates with toast system
export const useGlobalErrorHandler = () => {
  const { showError } = useToast();

  const handleError = useCallback((error: unknown, context?: string) => {
    // Log error for debugging/monitoring
    console.error('Global error handler:', error, context);
    
    // Show user-friendly error notification
    showError(error, context);
  }, [showError]);

  // Set up global error listeners
  React.useEffect(() => {
    const handleUnhandledError = (event: ErrorEvent) => {
      handleError(event.error, 'Unhandled JavaScript error');
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      handleError(event.reason, 'Unhandled Promise rejection');
    };

    // Add global error listeners
    window.addEventListener('error', handleUnhandledError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleUnhandledError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [handleError]);

  return { handleError };
};

export default ToastProvider;