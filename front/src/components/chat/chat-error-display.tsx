'use client';

import React, { useState } from 'react';
import { ChatError, ChatErrorHandler, ChatErrorUtils } from '@/lib/chat-error-handler';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { 
  AlertTriangle, 
  Wifi, 
  Shield, 
  Server, 
  Clock, 
  X, 
  ChevronDown, 
  ChevronUp,
  RefreshCw,
  LogIn
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatErrorDisplayProps {
  error: ChatError;
  onDismiss?: () => void;
  onRetry?: () => void;
  className?: string;
  compact?: boolean;
}

/**
 * Enhanced error display component for chat errors
 * Implements requirements 2.3 and 4.4 for user feedback and error handling
 */
export function ChatErrorDisplay({
  error,
  onDismiss,
  onRetry,
  className,
  compact = false
}: ChatErrorDisplayProps) {
  const [showDetails, setShowDetails] = useState(false);
  
  const errorDisplay = ChatErrorUtils.formatErrorForDisplay(error);
  const recoveryAction = ChatErrorHandler.getRecoveryAction(error);

  // Get appropriate icon for error type
  const getErrorIcon = () => {
    switch (error.type) {
      case 'network':
        return <Wifi className="h-5 w-5" />;
      case 'auth':
        return <Shield className="h-5 w-5" />;
      case 'server':
        return <Server className="h-5 w-5" />;
      case 'timeout':
        return <Clock className="h-5 w-5" />;
      default:
        return <AlertTriangle className="h-5 w-5" />;
    }
  };

  // Get color scheme based on severity
  const getColorScheme = () => {
    switch (errorDisplay.severity) {
      case 'error':
        return {
          bg: 'bg-red-50 border-red-200',
          text: 'text-red-800',
          icon: 'text-red-500',
          button: 'bg-red-600 hover:bg-red-700 text-white'
        };
      case 'warning':
        return {
          bg: 'bg-amber-50 border-amber-200',
          text: 'text-amber-800',
          icon: 'text-amber-500',
          button: 'bg-amber-600 hover:bg-amber-700 text-white'
        };
      case 'info':
        return {
          bg: 'bg-blue-50 border-blue-200',
          text: 'text-blue-800',
          icon: 'text-blue-500',
          button: 'bg-blue-600 hover:bg-blue-700 text-white'
        };
    }
  };

  const colors = getColorScheme();

  // Handle recovery action
  const handleRecoveryAction = () => {
    if (recoveryAction.action === 'retry_request' && onRetry) {
      onRetry();
    } else {
      recoveryAction.handler();
    }
  };

  // Compact version for inline display
  if (compact) {
    return (
      <div className={cn(
        'flex items-center gap-2 p-2 rounded-md border',
        colors.bg,
        className
      )}>
        <div className={colors.icon}>
          {getErrorIcon()}
        </div>
        <div className="flex-1 min-w-0">
          <p className={cn('text-sm font-medium', colors.text)}>
            {errorDisplay.title}
          </p>
          <p className={cn('text-xs', colors.text, 'opacity-80')}>
            {error.userMessage}
          </p>
        </div>
        {recoveryAction.canRecover && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleRecoveryAction}
            className="text-xs"
          >
            {recoveryAction.buttonText}
          </Button>
        )}
        {onDismiss && (
          <Button
            size="sm"
            variant="ghost"
            onClick={onDismiss}
            className="p-1 h-auto"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
    );
  }

  // Full error display
  return (
    <Card className={cn(
      'border',
      colors.bg,
      className
    )}>
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className={cn('flex-shrink-0 mt-0.5', colors.icon)}>
            {getErrorIcon()}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between">
              <div>
                <h3 className={cn('font-medium', colors.text)}>
                  {errorDisplay.title}
                </h3>
                <p className={cn('text-sm mt-1', colors.text, 'opacity-90')}>
                  {error.userMessage}
                </p>
              </div>
              
              {onDismiss && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onDismiss}
                  className="p-1 h-auto -mt-1 -mr-1"
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>

            {/* Error details (development mode or validation errors) */}
            {errorDisplay.showDetails && error.details && (
              <div className="mt-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowDetails(!showDetails)}
                  className="p-0 h-auto text-xs font-normal"
                >
                  <span className="mr-1">기술적 세부사항</span>
                  {showDetails ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                </Button>
                
                {showDetails && (
                  <div className="mt-2 p-3 bg-white/50 rounded border text-xs font-mono">
                    <div className="space-y-1">
                      <div><strong>Type:</strong> {error.type}</div>
                      <div><strong>Code:</strong> {error.code}</div>
                      {error.status && (
                        <div><strong>Status:</strong> {error.status}</div>
                      )}
                      <div><strong>Time:</strong> {error.timestamp.toLocaleString()}</div>
                      {error.details.context && (
                        <div>
                          <strong>Context:</strong>
                          <pre className="mt-1 text-xs overflow-auto">
                            {JSON.stringify(error.details.context, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-2 mt-4">
              {recoveryAction.canRecover && (
                <Button
                  size="sm"
                  onClick={handleRecoveryAction}
                  className={cn(
                    'flex items-center gap-2',
                    colors.button
                  )}
                >
                  {recoveryAction.action === 'retry_request' && (
                    <RefreshCw className="h-3 w-3" />
                  )}
                  {recoveryAction.action === 'redirect_login' && (
                    <LogIn className="h-3 w-3" />
                  )}
                  {recoveryAction.action === 'refresh_page' && (
                    <RefreshCw className="h-3 w-3" />
                  )}
                  {recoveryAction.buttonText}
                </Button>
              )}
              
              {onDismiss && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onDismiss}
                >
                  닫기
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * Error toast component for temporary error notifications
 */
interface ChatErrorToastProps {
  error: ChatError;
  onDismiss: () => void;
  autoHide?: boolean;
  hideDelay?: number;
}

export function ChatErrorToast({
  error,
  onDismiss,
  autoHide = true,
  hideDelay = 5000
}: ChatErrorToastProps) {
  React.useEffect(() => {
    if (autoHide) {
      const timer = setTimeout(onDismiss, hideDelay);
      return () => clearTimeout(timer);
    }
  }, [autoHide, hideDelay, onDismiss]);

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm">
      <ChatErrorDisplay
        error={error}
        onDismiss={onDismiss}
        compact={true}
        className="shadow-lg"
      />
    </div>
  );
}

/**
 * Error boundary fallback for chat-specific errors
 */
interface ChatErrorFallbackProps {
  error: Error;
  resetError: () => void;
}

export function ChatErrorFallback({ error, resetError }: ChatErrorFallbackProps) {
  const chatError = ChatErrorHandler.fromException(error, {
    endpoint: 'chat_component'
  });

  return (
    <div className="flex items-center justify-center p-8">
      <ChatErrorDisplay
        error={chatError}
        onRetry={resetError}
        className="max-w-md"
      />
    </div>
  );
}