'use client';

import React from 'react';
import { useChunkErrorHandler, useChunkHealthMonitor } from '@/hooks/use-chunk-error-handler';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  AlertTriangle, 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  Clock,
  Loader2 
} from 'lucide-react';

interface ChunkStatusIndicatorProps {
  showWhenHealthy?: boolean;
  compact?: boolean;
  className?: string;
}

/**
 * Component to display chunk loading status and provide retry options
 * Implements requirements 1.1, 1.3, 5.2 for user-friendly error display
 */
export function ChunkStatusIndicator({ 
  showWhenHealthy = false, 
  compact = false,
  className = '' 
}: ChunkStatusIndicatorProps) {
  const { failures, isRetrying, hasErrors, retryAllChunks, clearErrors } = useChunkErrorHandler();
  const healthStats = useChunkHealthMonitor();

  // Don't show anything if healthy and showWhenHealthy is false
  if (!hasErrors && !showWhenHealthy) {
    return null;
  }

  // Compact view for minimal UI impact
  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        {hasErrors ? (
          <>
            <Badge variant="destructive" className="flex items-center gap-1">
              <XCircle className="h-3 w-3" />
              {failures.length} chunk error{failures.length > 1 ? 's' : ''}
            </Badge>
            <Button
              size="sm"
              variant="outline"
              onClick={retryAllChunks}
              disabled={isRetrying}
              className="h-6 px-2 text-xs"
            >
              {isRetrying ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="h-3 w-3" />
              )}
            </Button>
          </>
        ) : (
          <Badge variant="secondary" className="flex items-center gap-1">
            <CheckCircle className="h-3 w-3" />
            All chunks loaded
          </Badge>
        )}
      </div>
    );
  }

  // Full status card
  return (
    <Card className={`p-4 ${className}`}>
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {hasErrors ? (
              <AlertTriangle className="h-5 w-5 text-amber-500" />
            ) : (
              <CheckCircle className="h-5 w-5 text-green-500" />
            )}
            <h3 className="font-medium">
              {hasErrors ? 'Resource Loading Issues' : 'All Resources Loaded'}
            </h3>
          </div>
          
          {hasErrors && (
            <Badge variant="destructive">
              {failures.length} error{failures.length > 1 ? 's' : ''}
            </Badge>
          )}
        </div>

        {/* Status message */}
        <p className="text-sm text-gray-600">
          {hasErrors ? (
            <>
              Some application resources failed to load. This may affect functionality.
              {healthStats.criticalFailures > 0 && (
                <span className="text-red-600 font-medium">
                  {' '}Critical resources are affected.
                </span>
              )}
            </>
          ) : (
            'All application resources have loaded successfully.'
          )}
        </p>

        {/* Failure details */}
        {hasErrors && failures.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700">Failed Resources:</h4>
            <div className="space-y-1">
              {failures.slice(0, 5).map((failure, index) => (
                <div key={index} className="flex items-center justify-between text-xs bg-gray-50 rounded p-2">
                  <span className="font-mono text-gray-700">{failure.chunkName}</span>
                  <div className="flex items-center gap-2 text-gray-500">
                    <Clock className="h-3 w-3" />
                    <span>{failure.attemptCount} attempt{failure.attemptCount > 1 ? 's' : ''}</span>
                  </div>
                </div>
              ))}
              {failures.length > 5 && (
                <div className="text-xs text-gray-500 text-center py-1">
                  ... and {failures.length - 5} more
                </div>
              )}
            </div>
          </div>
        )}

        {/* Health stats */}
        {showWhenHealthy && (
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Total Failures:</span>
              <span className="ml-2 font-medium">{healthStats.totalFailures}</span>
            </div>
            <div>
              <span className="text-gray-500">Critical Failures:</span>
              <span className="ml-2 font-medium">{healthStats.criticalFailures}</span>
            </div>
          </div>
        )}

        {/* Last failure time */}
        {healthStats.lastFailureTime && (
          <div className="text-xs text-gray-500">
            Last failure: {healthStats.lastFailureTime.toLocaleTimeString()}
          </div>
        )}

        {/* Actions */}
        {hasErrors && (
          <div className="flex gap-2 pt-2">
            <Button
              size="sm"
              onClick={retryAllChunks}
              disabled={isRetrying}
              className="flex items-center gap-2"
            >
              {isRetrying ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              {isRetrying ? 'Retrying...' : 'Retry All'}
            </Button>
            
            <Button
              size="sm"
              variant="outline"
              onClick={clearErrors}
              disabled={isRetrying}
            >
              Clear Errors
            </Button>
            
            <Button
              size="sm"
              variant="outline"
              onClick={() => window.location.reload()}
            >
              Reload Page
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}

/**
 * Floating chunk status indicator for minimal UI impact
 */
export function FloatingChunkStatus() {
  const { hasErrors, failures, isRetrying, retryAllChunks } = useChunkErrorHandler();

  if (!hasErrors) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <Card className="p-3 shadow-lg border-amber-200 bg-amber-50">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-amber-800">
              {failures.length} resource{failures.length > 1 ? 's' : ''} failed to load
            </p>
            <p className="text-xs text-amber-600">
              Some features may not work properly
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={retryAllChunks}
            disabled={isRetrying}
            className="border-amber-300 text-amber-700 hover:bg-amber-100"
          >
            {isRetrying ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              'Retry'
            )}
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default ChunkStatusIndicator;