/**
 * Integration tests for SSE-based real-time progress monitoring
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RealTimeProgressMonitor } from '../real-time-progress-monitor';
import { ETLJob } from '@/lib/types';

// Mock the SSE client
const mockSSEClient = {
  connect: vi.fn(),
  disconnect: vi.fn(),
  getConnectionState: vi.fn(() => ({
    isConnected: false,
    reconnectAttempts: 0,
  })),
};

vi.mock('@/lib/sse-client', () => ({
  useSSEClient: vi.fn(() => ({
    client: mockSSEClient,
    connectionState: {
      isConnected: false,
      reconnectAttempts: 0,
    },
    connect: mockSSEClient.connect,
    disconnect: mockSSEClient.disconnect,
  })),
  SSEClient: vi.fn(() => mockSSEClient),
}));

const mockRunningJob: ETLJob = {
  job_id: 'test-job-123',
  status: 'running',
  progress: 45,
  current_step: 'Processing documents',
  estimated_completion_time: new Date(Date.now() + 300000).toISOString(),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe('SSE Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('should establish SSE connection for running jobs', async () => {
    render(
      <TestWrapper>
        <RealTimeProgressMonitor initialJob={mockRunningJob} />
      </TestWrapper>
    );

    // Should show the progress monitor
    expect(screen.getByText('Job Progress')).toBeInTheDocument();
    expect(screen.getByText('Processing documents')).toBeInTheDocument();
    
    // Should attempt to connect
    await waitFor(() => {
      expect(mockSSEClient.connect).toHaveBeenCalled();
    });
  });

  it('should handle progress updates from SSE', async () => {
    const mockOnJobUpdate = vi.fn();
    const { useSSEClient } = await import('@/lib/sse-client');
    
    // Mock SSE client with progress callback
    let progressCallback: ((data: any) => void) | undefined;
    (useSSEClient as any).mockImplementation((jobId: string, options: any) => {
      progressCallback = options.onProgress;
      return {
        client: mockSSEClient,
        connectionState: { isConnected: true, reconnectAttempts: 0 },
        connect: mockSSEClient.connect,
        disconnect: mockSSEClient.disconnect,
      };
    });

    render(
      <TestWrapper>
        <RealTimeProgressMonitor 
          initialJob={mockRunningJob} 
          onJobUpdate={mockOnJobUpdate}
        />
      </TestWrapper>
    );

    // Simulate progress update
    if (progressCallback) {
      act(() => {
        progressCallback({
          job_id: 'test-job-123',
          progress: 75,
          current_step: 'Finalizing processing',
          status: 'running',
        });
      });
    }

    // Should update the UI
    await waitFor(() => {
      expect(screen.getByText('Finalizing processing')).toBeInTheDocument();
      expect(screen.getByText('75%')).toBeInTheDocument();
    });

    // Should call the update callback
    expect(mockOnJobUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        progress: 75,
        current_step: 'Finalizing processing',
      })
    );
  });

  it('should handle job completion through SSE', async () => {
    const { useSSEClient } = await import('@/lib/sse-client');
    
    let progressCallback: ((data: any) => void) | undefined;
    (useSSEClient as any).mockImplementation((jobId: string, options: any) => {
      progressCallback = options.onProgress;
      return {
        client: mockSSEClient,
        connectionState: { isConnected: true, reconnectAttempts: 0 },
        connect: mockSSEClient.connect,
        disconnect: mockSSEClient.disconnect,
      };
    });

    render(
      <TestWrapper>
        <RealTimeProgressMonitor initialJob={mockRunningJob} />
      </TestWrapper>
    );

    // Simulate job completion
    if (progressCallback) {
      act(() => {
        progressCallback({
          job_id: 'test-job-123',
          progress: 100,
          current_step: 'Completed successfully',
          status: 'completed',
        });
      });
    }

    // Should show completion status
    await waitFor(() => {
      expect(screen.getByText('Job Completed Successfully')).toBeInTheDocument();
      expect(screen.getByText(/All data has been successfully transformed/)).toBeInTheDocument();
    });
  });

  it('should handle connection failures gracefully', async () => {
    const { useSSEClient } = await import('@/lib/sse-client');
    
    // Mock failed connection
    (useSSEClient as any).mockImplementation(() => ({
      client: mockSSEClient,
      connectionState: { 
        isConnected: false, 
        reconnectAttempts: 3,
        lastError: 'Connection failed' 
      },
      connect: mockSSEClient.connect,
      disconnect: mockSSEClient.disconnect,
    }));

    render(
      <TestWrapper>
        <RealTimeProgressMonitor initialJob={mockRunningJob} />
      </TestWrapper>
    );

    // Should show connection issues
    await waitFor(() => {
      expect(screen.getByText('Connection Issues')).toBeInTheDocument();
      expect(screen.getByText(/Unable to establish real-time connection/)).toBeInTheDocument();
    });
  });

  it('should not connect for completed jobs', () => {
    const completedJob: ETLJob = {
      ...mockRunningJob,
      status: 'completed',
      progress: 100,
    };

    render(
      <TestWrapper>
        <RealTimeProgressMonitor initialJob={completedJob} />
      </TestWrapper>
    );

    // Should not show connection status for completed jobs
    expect(screen.queryByText('Real-time Updates')).not.toBeInTheDocument();
    
    // Should not attempt to connect
    expect(mockSSEClient.connect).not.toHaveBeenCalled();
  });

  it('should handle manual disconnect and reconnect', async () => {
    const { useSSEClient } = await import('@/lib/sse-client');
    
    (useSSEClient as any).mockImplementation(() => ({
      client: mockSSEClient,
      connectionState: { isConnected: true, reconnectAttempts: 0 },
      connect: mockSSEClient.connect,
      disconnect: mockSSEClient.disconnect,
    }));

    render(
      <TestWrapper>
        <RealTimeProgressMonitor initialJob={mockRunningJob} />
      </TestWrapper>
    );

    // Should show disconnect button when connected
    const disconnectButton = screen.getByText('🔌 Disconnect');
    expect(disconnectButton).toBeInTheDocument();

    // Click disconnect
    disconnectButton.click();
    expect(mockSSEClient.disconnect).toHaveBeenCalled();
  });
});