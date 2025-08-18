'use client';

import { useState, useEffect, useCallback } from 'react';
import { chunkErrorHandler, ChunkLoadError } from '@/lib/chunk-error-handler';

interface ChunkErrorState {
  failures: ChunkLoadError[];
  isRetrying: boolean;
  hasErrors: boolean;
}

interface ChunkErrorActions {
  retryChunk: (chunkName: string) => Promise<boolean>;
  retryAllChunks: () => Promise<void>;
  clearErrors: () => void;
  reloadPage: () => void;
}

/**
 * Hook for handling chunk loading errors in components
 * Provides state and actions for chunk error management
 */
export function useChunkErrorHandler(): ChunkErrorState & ChunkErrorActions {
  const [state, setState] = useState<ChunkErrorState>({
    failures: [],
    isRetrying: false,
    hasErrors: false,
  });

  // Update state when chunk failures occur
  const updateFailures = useCallback(() => {
    const failures = chunkErrorHandler.getFailureStats();
    setState(prev => ({
      ...prev,
      failures,
      hasErrors: failures.length > 0,
    }));
  }, []);

  // Listen for chunk error events
  useEffect(() => {
    const handleChunkRetryNeeded = (event: CustomEvent) => {
      console.log('Chunk retry needed:', event.detail);
      updateFailures();
    };

    const handleChunkFallback = (event: CustomEvent) => {
      console.log('Chunk fallback triggered:', event.detail);
      updateFailures();
    };

    // Add event listeners
    window.addEventListener('chunk:retry-needed', handleChunkRetryNeeded as EventListener);
    window.addEventListener('chunk:fallback', handleChunkFallback as EventListener);

    // Initial state update
    updateFailures();

    // Cleanup
    return () => {
      window.removeEventListener('chunk:retry-needed', handleChunkRetryNeeded as EventListener);
      window.removeEventListener('chunk:fallback', handleChunkFallback as EventListener);
    };
  }, [updateFailures]);

  // Retry a specific chunk
  const retryChunk = useCallback(async (chunkName: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isRetrying: true }));
    
    try {
      const success = await chunkErrorHandler.manualRetry(chunkName);
      
      if (success) {
        // Update failures after successful retry
        updateFailures();
      }
      
      return success;
    } catch (error) {
      console.error(`Failed to retry chunk ${chunkName}:`, error);
      return false;
    } finally {
      setState(prev => ({ ...prev, isRetrying: false }));
    }
  }, [updateFailures]);

  // Retry all failed chunks
  const retryAllChunks = useCallback(async (): Promise<void> => {
    setState(prev => ({ ...prev, isRetrying: true }));
    
    try {
      const failures = chunkErrorHandler.getFailureStats();
      const retryPromises = failures.map(failure => 
        chunkErrorHandler.manualRetry(failure.chunkName)
      );
      
      await Promise.allSettled(retryPromises);
      
      // Update failures after retry attempts
      updateFailures();
    } catch (error) {
      console.error('Failed to retry chunks:', error);
    } finally {
      setState(prev => ({ ...prev, isRetrying: false }));
    }
  }, [updateFailures]);

  // Clear all chunk errors
  const clearErrors = useCallback(() => {
    chunkErrorHandler.clearFailureHistory();
    setState({
      failures: [],
      isRetrying: false,
      hasErrors: false,
    });
  }, []);

  // Reload the page as fallback
  const reloadPage = useCallback(() => {
    window.location.reload();
  }, []);

  return {
    // State
    failures: state.failures,
    isRetrying: state.isRetrying,
    hasErrors: state.hasErrors,
    
    // Actions
    retryChunk,
    retryAllChunks,
    clearErrors,
    reloadPage,
  };
}

/**
 * Hook for monitoring chunk loading health
 * Provides statistics and health indicators
 */
export function useChunkHealthMonitor() {
  const [healthStats, setHealthStats] = useState({
    totalFailures: 0,
    criticalFailures: 0,
    lastFailureTime: null as Date | null,
    isHealthy: true,
  });

  useEffect(() => {
    const updateHealthStats = () => {
      const failures = chunkErrorHandler.getFailureStats();
      const criticalFailures = failures.filter(f => 
        f.chunkName.includes('main') || 
        f.chunkName.includes('app') || 
        f.chunkName.includes('layout')
      );

      const lastFailure = failures.length > 0 
        ? failures.reduce((latest, current) => 
            current.timestamp > latest.timestamp ? current : latest
          )
        : null;

      setHealthStats({
        totalFailures: failures.length,
        criticalFailures: criticalFailures.length,
        lastFailureTime: lastFailure?.timestamp || null,
        isHealthy: failures.length === 0,
      });
    };

    // Listen for chunk events
    const handleChunkEvent = () => updateHealthStats();
    
    window.addEventListener('chunk:retry-needed', handleChunkEvent);
    window.addEventListener('chunk:fallback', handleChunkEvent);
    
    // Initial update
    updateHealthStats();
    
    // Periodic health check
    const healthCheckInterval = setInterval(updateHealthStats, 30000); // Every 30 seconds
    
    return () => {
      window.removeEventListener('chunk:retry-needed', handleChunkEvent);
      window.removeEventListener('chunk:fallback', handleChunkEvent);
      clearInterval(healthCheckInterval);
    };
  }, []);

  return healthStats;
}

/**
 * Hook for handling dynamic imports with chunk error recovery
 */
export function useDynamicImportWithRetry<T = any>(
  importFn: () => Promise<T>,
  options: {
    maxRetries?: number;
    retryDelay?: number;
    fallback?: T;
  } = {}
) {
  const [state, setState] = useState<{
    data: T | null;
    loading: boolean;
    error: Error | null;
    retryCount: number;
  }>({
    data: null,
    loading: false,
    error: null,
    retryCount: 0,
  });

  const { maxRetries = 3, retryDelay = 1000, fallback } = options;

  const executeImport = useCallback(async (retryCount = 0): Promise<void> => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const result = await importFn();
      setState({
        data: result,
        loading: false,
        error: null,
        retryCount,
      });
    } catch (error) {
      const importError = error as Error;
      
      // Check if this is a chunk loading error
      const isChunkError = importError.message?.includes('Loading chunk') ||
                          importError.message?.includes('Loading CSS chunk');

      if (isChunkError && retryCount < maxRetries) {
        // Wait before retrying
        await new Promise(resolve => setTimeout(resolve, retryDelay * Math.pow(2, retryCount)));
        
        // Retry the import
        return executeImport(retryCount + 1);
      } else {
        // Use fallback if available
        setState({
          data: fallback || null,
          loading: false,
          error: importError,
          retryCount,
        });
      }
    }
  }, [importFn, maxRetries, retryDelay, fallback]);

  const retry = useCallback(() => {
    executeImport(0);
  }, [executeImport]);

  return {
    ...state,
    retry,
    executeImport: () => executeImport(0),
  };
}