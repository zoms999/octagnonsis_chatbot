/**
 * Hook for managing ETL job progress monitoring with SSE
 */

import { useState, useEffect, useCallback } from 'react';
import { ETLJob } from '@/lib/types';
import { useSSEClient, SSEProgressData } from '@/lib/sse-client';

interface UseETLProgressOptions {
  autoConnect?: boolean;
  onJobComplete?: (job: ETLJob) => void;
  onJobFailed?: (job: ETLJob) => void;
}

interface UseETLProgressReturn {
  currentJob: ETLJob;
  isConnected: boolean;
  connectionState: {
    isConnected: boolean;
    reconnectAttempts: number;
    lastError?: string;
  };
  connect: () => void;
  disconnect: () => void;
  refresh: () => void;
}

export function useETLProgress(
  initialJob: ETLJob,
  options: UseETLProgressOptions = {}
): UseETLProgressReturn {
  const { autoConnect = true, onJobComplete, onJobFailed } = options;
  
  const [currentJob, setCurrentJob] = useState<ETLJob>(initialJob);
  const [isManuallyDisconnected, setIsManuallyDisconnected] = useState(false);

  // Handle progress updates from SSE
  const handleProgress = useCallback((data: SSEProgressData) => {
    const updatedJob: ETLJob = {
      ...currentJob,
      job_id: data.job_id,
      progress: data.progress,
      current_step: data.current_step,
      status: data.status,
      estimated_completion_time: data.estimated_completion_time,
      error_message: data.error_message,
      updated_at: new Date().toISOString(),
    };

    setCurrentJob(updatedJob);

    // Trigger completion callbacks
    if (data.status === 'completed' && currentJob.status !== 'completed') {
      onJobComplete?.(updatedJob);
    } else if (data.status === 'failed' && currentJob.status !== 'failed') {
      onJobFailed?.(updatedJob);
    }
  }, [currentJob, onJobComplete, onJobFailed]);

  // Determine if we should connect to SSE
  const shouldConnect = currentJob.status === 'running' || currentJob.status === 'pending';
  const jobId = shouldConnect && !isManuallyDisconnected ? currentJob.job_id : null;

  // Initialize SSE client
  const { client, connectionState, connect: sseConnect, disconnect: sseDisconnect } = useSSEClient(jobId, {
    onProgress: handleProgress,
    onError: (error) => {
      console.error('ETL Progress SSE error:', error);
    },
    maxReconnectAttempts: 5,
    reconnectDelay: 1000,
  });

  // Auto-connect when component mounts if job is active
  useEffect(() => {
    if (autoConnect && shouldConnect && !isManuallyDisconnected) {
      sseConnect();
    }
  }, [autoConnect, shouldConnect, isManuallyDisconnected, sseConnect]);

  // Update job when prop changes
  useEffect(() => {
    setCurrentJob(initialJob);
  }, [initialJob]);

  // Manual connection controls
  const connect = useCallback(() => {
    setIsManuallyDisconnected(false);
    sseConnect();
  }, [sseConnect]);

  const disconnect = useCallback(() => {
    setIsManuallyDisconnected(true);
    sseDisconnect();
  }, [sseDisconnect]);

  // Refresh job data (useful for manual updates)
  const refresh = useCallback(() => {
    // This could trigger a refetch from the parent component
    // For now, we'll just reconnect if the job is active
    if (shouldConnect) {
      sseDisconnect();
      setTimeout(() => sseConnect(), 100);
    }
  }, [shouldConnect, sseConnect, sseDisconnect]);

  return {
    currentJob,
    isConnected: connectionState.isConnected,
    connectionState,
    connect,
    disconnect,
    refresh,
  };
}

/**
 * Hook for monitoring multiple ETL jobs simultaneously
 */
export function useMultipleETLProgress(
  jobs: ETLJob[],
  options: UseETLProgressOptions = {}
): {
  jobs: ETLJob[];
  activeConnections: number;
  connectAll: () => void;
  disconnectAll: () => void;
} {
  const [currentJobs, setCurrentJobs] = useState<ETLJob[]>(jobs);
  const [connections, setConnections] = useState<Map<string, boolean>>(new Map());

  // Update jobs when prop changes
  useEffect(() => {
    setCurrentJobs(jobs);
  }, [jobs]);

  // Track active connections
  const activeConnections = Array.from(connections.values()).filter(Boolean).length;

  const connectAll = useCallback(() => {
    // This would need to be implemented with multiple SSE clients
    // For now, this is a placeholder
    console.log('Connect all ETL progress monitors');
  }, []);

  const disconnectAll = useCallback(() => {
    // This would need to be implemented with multiple SSE clients
    // For now, this is a placeholder
    console.log('Disconnect all ETL progress monitors');
  }, []);

  return {
    jobs: currentJobs,
    activeConnections,
    connectAll,
    disconnectAll,
  };
}