'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { chunkErrorHandler, ChunkLoadError } from '@/lib/chunk-error-handler';
import { ErrorHandler } from '@/lib/error-handling';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { AlertTriangle, RefreshCw, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: (error: Error, errorInfo: ErrorInfo, retryHandler: () => void) => ReactNode;
  onChunkError?: (chunkName: string, error: ChunkLoadError) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  chunkFailures: ChunkLoadError[];
  isRetrying: boolean;
}

/**
 * Specialized Error Boundary for handling chunk loading failures
 * Implements requirements 1.1, 1.3, 5.2 for chunk error handling
 */
export class ChunkErrorBoundary extends Component<Props, State> {
  private chunkRetryListener?: (event: CustomEvent) => void;
  private chunkFallbackListener?: (event: CustomEvent) => void;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      chunkFailures: [],
      isRetrying: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Check if this is a chunk loading error
    const isChunkError = error.message?.includes('Loading chunk') ||
                        error.message?.includes('Loading CSS chunk') ||
                        error.name === 'ChunkLoadError';

    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error for monitoring
    ErrorHandler.logError(error, 'ChunkErrorBoundary');
    
    // Store error info in state
    this.setState({
      error,
      errorInfo,
      chunkFailures: chunkErrorHandler.getFailureStats(),
    });

    // Check if this is a chunk-related error
    const isChunkError = this.isChunkRelatedError(error);
    
    if (isChunkError) {
      console.warn('Chunk loading error caught by boundary:', error);
      
      // Get current chunk failures
      const failures = chunkErrorHandler.getFailureStats();
      this.setState({ chunkFailures: failures });
      
      // Notify parent component if callback provided
      if (this.props.onChunkError && failures.length > 0) {
        const latestFailure = failures[failures.length - 1];
        this.props.onChunkError(latestFailure.chunkName, latestFailure);
      }
    }
  }

  componentDidMount() {
    // Listen for chunk retry events
    this.chunkRetryListener = (event: CustomEvent) => {
      const { chunkName } = event.detail;
      console.log(`Chunk retry needed for: ${chunkName}`);
      this.setState({ chunkFailures: chunkErrorHandler.getFailureStats() });
    };

    // Listen for chunk fallback events
    this.chunkFallbackListener = (event: CustomEvent) => {
      const { chunkName, failure } = event.detail;
      console.log(`Chunk fallback triggered for: ${chunkName}`);
      
      this.setState({ 
        chunkFailures: chunkErrorHandler.getFailureStats(),
        hasError: true,
        error: new Error(`Critical chunk failed to load: ${chunkName}`),
      });
      
      if (this.props.onChunkError) {
        this.props.onChunkError(chunkName, failure);
      }
    };

    window.addEventListener('chunk:retry-needed', this.chunkRetryListener as EventListener);
    window.addEventListener('chunk:fallback', this.chunkFallbackListener as EventListener);
  }

  componentWillUnmount() {
    if (this.chunkRetryListener) {
      window.removeEventListener('chunk:retry-needed', this.chunkRetryListener as EventListener);
    }
    if (this.chunkFallbackListener) {
      window.removeEventListener('chunk:fallback', this.chunkFallbackListener as EventListener);
    }
  }

  /**
   * Check if error is related to chunk loading
   */
  private isChunkRelatedError(error: Error): boolean {
    const chunkErrorPatterns = [
      'Loading chunk',
      'Loading CSS chunk',
      'ChunkLoadError',
      'Failed to import',
      'Script error',
    ];

    return chunkErrorPatterns.some(pattern => 
      error.message?.includes(pattern) || error.name?.includes(pattern)
    );
  }

  /**
   * Reset error boundary and clear chunk failures
   */
  private resetErrorBoundary = () => {
    chunkErrorHandler.clearFailureHistory();
    this.setState({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
      chunkFailures: [],
      isRetrying: false,
    });
  };

  /**
   * Retry failed chunks
   */
  private handleRetryChunks = async () => {
    this.setState({ isRetrying: true });

    try {
      const failures = this.state.chunkFailures;
      let retrySuccess = false;

      for (const failure of failures) {
        const success = await chunkErrorHandler.manualRetry(failure.chunkName);
        if (success) {
          retrySuccess = true;
        }
      }

      if (retrySuccess) {
        // If any retry succeeded, reset the boundary
        this.resetErrorBoundary();
      } else {
        // If all retries failed, update the failure list
        this.setState({ 
          chunkFailures: chunkErrorHandler.getFailureStats(),
          isRetrying: false,
        });
      }
    } catch (error) {
      console.error('Error during chunk retry:', error);
      this.setState({ isRetrying: false });
    }
  };

  /**
   * Reload the entire page as fallback
   */
  private handlePageReload = () => {
    window.location.reload();
  };

  /**
   * Render chunk-specific error UI
   */
  private renderChunkErrorUI() {
    const { chunkFailures, isRetrying } = this.state;
    const hasChunkFailures = chunkFailures.length > 0;

    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
        <Card className="w-full max-w-lg p-6">
          <div className="text-center space-y-4">
            <div className="flex justify-center">
              <AlertTriangle className="h-12 w-12 text-amber-500" />
            </div>
            
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Loading Error
              </h2>
              <p className="text-gray-600 mb-4">
                Some application resources failed to load. This might be due to a network issue or server problem.
              </p>
            </div>

            {hasChunkFailures && (
              <div className="bg-gray-50 rounded-lg p-4 text-left">
                <h3 className="font-medium text-gray-900 mb-2">Failed Resources:</h3>
                <ul className="text-sm text-gray-600 space-y-1">
                  {chunkFailures.map((failure, index) => (
                    <li key={index} className="flex justify-between items-center">
                      <span className="font-mono text-xs">{failure.chunkName}</span>
                      <span className="text-xs text-gray-500">
                        {failure.attemptCount} attempt{failure.attemptCount > 1 ? 's' : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button
                onClick={this.handleRetryChunks}
                disabled={isRetrying}
                variant="outline"
                size="sm"
                className="flex items-center gap-2"
              >
                {isRetrying ? (
                  <RotateCcw className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                {isRetrying ? 'Retrying...' : 'Retry Loading'}
              </Button>
              
              <Button
                onClick={this.handlePageReload}
                size="sm"
                className="flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Reload Page
              </Button>
            </div>

            <p className="text-xs text-gray-500">
              If this problem persists, please check your internet connection or try again later.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  /**
   * Render generic error UI for non-chunk errors
   */
  private renderGenericErrorUI() {
    const { error, errorInfo } = this.state;

    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
        <Card className="w-full max-w-md p-6 text-center">
          <div className="mb-4">
            <AlertTriangle className="mx-auto h-12 w-12 text-red-500" />
          </div>
          
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            Something went wrong
          </h2>
          
          <p className="text-sm text-gray-600 mb-6">
            {process.env.NODE_ENV === 'development' && error
              ? error.message 
              : 'An unexpected error occurred. Please refresh the page.'}
          </p>

          {process.env.NODE_ENV === 'development' && error && errorInfo && (
            <details className="mb-6 text-left">
              <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
                Technical Details
              </summary>
              <div className="mt-2 p-3 bg-gray-100 rounded text-xs font-mono text-gray-800 overflow-auto max-h-32">
                <pre>{error.toString()}</pre>
                <pre>{errorInfo.componentStack}</pre>
              </div>
            </details>
          )}

          <div className="flex gap-3 justify-center">
            <Button
              onClick={this.resetErrorBoundary}
              variant="outline"
              size="sm"
            >
              Try Again
            </Button>
            <Button
              onClick={this.handlePageReload}
              size="sm"
            >
              Reload Page
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback && this.state.error && this.state.errorInfo) {
        return this.props.fallback(
          this.state.error, 
          this.state.errorInfo, 
          this.resetErrorBoundary
        );
      }

      // Check if this is a chunk-related error
      const isChunkError = this.state.error && this.isChunkRelatedError(this.state.error);
      const hasChunkFailures = this.state.chunkFailures.length > 0;

      if (isChunkError || hasChunkFailures) {
        return this.renderChunkErrorUI();
      } else {
        return this.renderGenericErrorUI();
      }
    }

    return this.props.children;
  }
}

export default ChunkErrorBoundary;