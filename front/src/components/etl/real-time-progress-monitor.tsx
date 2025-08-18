'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { ETLJob } from '@/lib/types';
import { useSSEClient, SSEProgressData, SSEConnectionState } from '@/lib/sse-client';
import { ProgressBar } from './progress-bar';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/loading';

interface RealTimeProgressMonitorProps {
  initialJob: ETLJob;
  onJobUpdate?: (job: ETLJob) => void;
  autoConnect?: boolean;
}

export function RealTimeProgressMonitor({ 
  initialJob, 
  onJobUpdate,
  autoConnect = true 
}: RealTimeProgressMonitorProps) {
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
    onJobUpdate?.(updatedJob);
  }, [currentJob, onJobUpdate]);

  // Handle connection state changes
  const handleConnectionChange = useCallback((state: SSEConnectionState) => {
    // Log connection state changes for debugging
    console.log('SSE Connection state changed:', state);
  }, []);

  // Handle SSE errors
  const handleError = useCallback((error: Event) => {
    console.error('SSE connection error:', error);
  }, []);

  // Determine if we should connect to SSE
  const shouldConnect = currentJob.status === 'running' || currentJob.status === 'pending';
  const jobId = shouldConnect && !isManuallyDisconnected ? currentJob.job_id : null;

  // Initialize SSE client
  const { client, connectionState, connect, disconnect } = useSSEClient(jobId, {
    onProgress: handleProgress,
    onError: handleError,
    onConnectionChange: handleConnectionChange,
    maxReconnectAttempts: 5,
    reconnectDelay: 1000,
  });

  // Auto-connect when component mounts if job is active
  useEffect(() => {
    if (autoConnect && shouldConnect && !isManuallyDisconnected) {
      connect();
    }
  }, [autoConnect, shouldConnect, isManuallyDisconnected, connect]);

  // Update job when prop changes
  useEffect(() => {
    setCurrentJob(initialJob);
  }, [initialJob]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  const handleManualConnect = () => {
    setIsManuallyDisconnected(false);
    connect();
  };

  const handleManualDisconnect = () => {
    setIsManuallyDisconnected(true);
    disconnect();
  };

  const isConnected = connectionState.isConnected;
  const canConnect = shouldConnect && !isConnected;
  const canDisconnect = shouldConnect && isConnected;

  return (
    <div className="space-y-4">
      {/* Connection Status */}
      {shouldConnect && (
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border">
          <div className="flex items-center space-x-3">
            <div className={`
              w-3 h-3 rounded-full
              ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}
            `} />
            <div>
              <span className="text-sm font-medium text-gray-900">
                Real-time Updates
              </span>
              <p className="text-xs text-gray-600">
                {isConnected 
                  ? 'Connected - receiving live progress updates'
                  : connectionState.reconnectAttempts > 0
                    ? `Reconnecting... (attempt ${connectionState.reconnectAttempts})`
                    : 'Disconnected - no live updates'
                }
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {canConnect && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleManualConnect}
                className="text-green-600 border-green-300 hover:bg-green-50"
              >
                🔌 Connect
              </Button>
            )}
            {canDisconnect && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleManualDisconnect}
                className="text-red-600 border-red-300 hover:bg-red-50"
              >
                🔌 Disconnect
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Progress Display */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Job Progress
          </h3>
          <div className="flex items-center space-x-2">
            {isConnected && shouldConnect && (
              <div className="flex items-center space-x-1 text-green-600">
                <Spinner size="sm" />
                <span className="text-xs font-medium">Live</span>
              </div>
            )}
            <span className="text-sm text-gray-500 font-mono">
              {currentJob.job_id.slice(0, 8)}...
            </span>
          </div>
        </div>

        <ProgressBar 
          job={currentJob} 
          showDetails={true}
          size="lg"
          animated={shouldConnect}
        />
      </div>

      {/* Connection Troubleshooting */}
      {shouldConnect && !isConnected && connectionState.reconnectAttempts >= 3 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <span className="text-yellow-600 text-lg">⚠️</span>
            <div>
              <h4 className="text-sm font-medium text-yellow-800">
                Connection Issues
              </h4>
              <p className="text-sm text-yellow-700 mt-1">
                Unable to establish real-time connection after multiple attempts. 
                You can still monitor progress by refreshing the page or clicking reconnect.
              </p>
              <div className="mt-3">
                <Button
                  size="sm"
                  onClick={handleManualConnect}
                  className="bg-yellow-600 hover:bg-yellow-700 text-white"
                >
                  🔄 Try Again
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Job Completion Status */}
      {currentJob.status === 'completed' && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <span className="text-green-600 text-lg">✅</span>
            <div>
              <h4 className="text-sm font-medium text-green-800">
                Job Completed Successfully
              </h4>
              <p className="text-sm text-green-700 mt-1">
                Your ETL job has finished processing. All data has been successfully transformed and stored.
              </p>
            </div>
          </div>
        </div>
      )}

      {currentJob.status === 'failed' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center space-x-3">
            <span className="text-red-600 text-lg">❌</span>
            <div>
              <h4 className="text-sm font-medium text-red-800">
                Job Failed
              </h4>
              <p className="text-sm text-red-700 mt-1">
                The ETL job encountered an error and could not complete successfully.
              </p>
              {currentJob.error_message && (
                <div className="mt-2 p-2 bg-red-100 rounded border text-sm text-red-800">
                  {currentJob.error_message}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}