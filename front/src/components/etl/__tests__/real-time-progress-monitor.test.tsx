/**
 * Tests for real-time progress monitor component
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RealTimeProgressMonitor } from '../real-time-progress-monitor';
import { ETLJob } from '@/lib/types';

// Mock the SSE client hook
vi.mock('@/lib/sse-client', () => ({
  useSSEClient: vi.fn(() => ({
    client: null,
    connectionState: {
      isConnected: false,
      reconnectAttempts: 0,
    },
    connect: vi.fn(),
    disconnect: vi.fn(),
  })),
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

const mockCompletedJob: ETLJob = {
  ...mockRunningJob,
  status: 'completed',
  progress: 100,
  current_step: 'Completed successfully',
};

const mockFailedJob: ETLJob = {
  ...mockRunningJob,
  status: 'failed',
  progress: 30,
  current_step: 'Failed during processing',
  error_message: 'Database connection timeout',
};

describe('RealTimeProgressMonitor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render progress monitor for running job', () => {
    render(<RealTimeProgressMonitor initialJob={mockRunningJob} />);
    
    expect(screen.getByText('Real-time Updates')).toBeInTheDocument();
    expect(screen.getByText('Job Progress')).toBeInTheDocument();
    expect(screen.getByText('Processing documents')).toBeInTheDocument();
    expect(screen.getByText('45%')).toBeInTheDocument();
  });

  it('should show connection status for active jobs', () => {
    render(<RealTimeProgressMonitor initialJob={mockRunningJob} />);
    
    expect(screen.getByText('Disconnected - no live updates')).toBeInTheDocument();
  });

  it('should show completed status for finished jobs', () => {
    render(<RealTimeProgressMonitor initialJob={mockCompletedJob} />);
    
    expect(screen.getByText('Job Completed Successfully')).toBeInTheDocument();
    expect(screen.getByText(/All data has been successfully transformed/)).toBeInTheDocument();
  });

  it('should show failed status with error message', () => {
    render(<RealTimeProgressMonitor initialJob={mockFailedJob} />);
    
    expect(screen.getByText('Job Failed')).toBeInTheDocument();
    expect(screen.getByText('Database connection timeout')).toBeInTheDocument();
  });

  it('should handle job updates through callback', async () => {
    const mockOnJobUpdate = vi.fn();
    
    render(
      <RealTimeProgressMonitor 
        initialJob={mockRunningJob} 
        onJobUpdate={mockOnJobUpdate}
      />
    );
    
    // The component should be rendered
    expect(screen.getByText('Processing documents')).toBeInTheDocument();
  });

  it('should not show connection status for completed jobs', () => {
    render(<RealTimeProgressMonitor initialJob={mockCompletedJob} />);
    
    expect(screen.queryByText('Real-time Updates')).not.toBeInTheDocument();
  });

  it('should not show connection status for failed jobs', () => {
    render(<RealTimeProgressMonitor initialJob={mockFailedJob} />);
    
    expect(screen.queryByText('Real-time Updates')).not.toBeInTheDocument();
  });

  it('should handle autoConnect prop', () => {
    const { rerender } = render(
      <RealTimeProgressMonitor 
        initialJob={mockRunningJob} 
        autoConnect={false}
      />
    );
    
    expect(screen.getByText('Real-time Updates')).toBeInTheDocument();
    
    rerender(
      <RealTimeProgressMonitor 
        initialJob={mockCompletedJob} 
        autoConnect={false}
      />
    );
    
    expect(screen.queryByText('Real-time Updates')).not.toBeInTheDocument();
  });

  it('should show job ID in progress section', () => {
    render(<RealTimeProgressMonitor initialJob={mockRunningJob} />);
    
    expect(screen.getByText('test-job-...')).toBeInTheDocument();
  });

  it('should handle jobs without estimated completion time', () => {
    const jobWithoutETA: ETLJob = {
      ...mockRunningJob,
      estimated_completion_time: undefined,
    };
    
    render(<RealTimeProgressMonitor initialJob={jobWithoutETA} />);
    
    expect(screen.getByText('Processing documents')).toBeInTheDocument();
    expect(screen.queryByText(/ETA:/)).not.toBeInTheDocument();
  });

  it('should handle jobs without current step', () => {
    const jobWithoutStep: ETLJob = {
      ...mockRunningJob,
      current_step: '',
    };
    
    render(<RealTimeProgressMonitor initialJob={jobWithoutStep} />);
    
    expect(screen.getByText('Initializing...')).toBeInTheDocument();
  });
});

describe('RealTimeProgressMonitor - Connection Management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show connect button when disconnected', () => {
    // Mock disconnected state
    const { useSSEClient } = require('@/lib/sse-client');
    useSSEClient.mockReturnValue({
      client: null,
      connectionState: {
        isConnected: false,
        reconnectAttempts: 0,
      },
      connect: vi.fn(),
      disconnect: vi.fn(),
    });

    render(<RealTimeProgressMonitor initialJob={mockRunningJob} />);
    
    expect(screen.getByText('🔌 Connect')).toBeInTheDocument();
  });

  it('should show disconnect button when connected', () => {
    // Mock connected state
    const { useSSEClient } = require('@/lib/sse-client');
    useSSEClient.mockReturnValue({
      client: {},
      connectionState: {
        isConnected: true,
        reconnectAttempts: 0,
      },
      connect: vi.fn(),
      disconnect: vi.fn(),
    });

    render(<RealTimeProgressMonitor initialJob={mockRunningJob} />);
    
    expect(screen.getByText('🔌 Disconnect')).toBeInTheDocument();
    expect(screen.getByText('Connected - receiving live progress updates')).toBeInTheDocument();
  });

  it('should call connect when connect button is clicked', () => {
    const mockConnect = vi.fn();
    const { useSSEClient } = require('@/lib/sse-client');
    useSSEClient.mockReturnValue({
      client: null,
      connectionState: {
        isConnected: false,
        reconnectAttempts: 0,
      },
      connect: mockConnect,
      disconnect: vi.fn(),
    });

    render(<RealTimeProgressMonitor initialJob={mockRunningJob} />);
    
    const connectButton = screen.getByText('🔌 Connect');
    fireEvent.click(connectButton);
    
    expect(mockConnect).toHaveBeenCalled();
  });

  it('should call disconnect when disconnect button is clicked', () => {
    const mockDisconnect = vi.fn();
    const { useSSEClient } = require('@/lib/sse-client');
    useSSEClient.mockReturnValue({
      client: {},
      connectionState: {
        isConnected: true,
        reconnectAttempts: 0,
      },
      connect: vi.fn(),
      disconnect: mockDisconnect,
    });

    render(<RealTimeProgressMonitor initialJob={mockRunningJob} />);
    
    const disconnectButton = screen.getByText('🔌 Disconnect');
    fireEvent.click(disconnectButton);
    
    expect(mockDisconnect).toHaveBeenCalled();
  });

  it('should show reconnection attempts', () => {
    const { useSSEClient } = require('@/lib/sse-client');
    useSSEClient.mockReturnValue({
      client: null,
      connectionState: {
        isConnected: false,
        reconnectAttempts: 2,
      },
      connect: vi.fn(),
      disconnect: vi.fn(),
    });

    render(<RealTimeProgressMonitor initialJob={mockRunningJob} />);
    
    expect(screen.getByText('Reconnecting... (attempt 2)')).toBeInTheDocument();
  });

  it('should show connection troubleshooting after multiple failed attempts', () => {
    const { useSSEClient } = require('@/lib/sse-client');
    useSSEClient.mockReturnValue({
      client: null,
      connectionState: {
        isConnected: false,
        reconnectAttempts: 5,
      },
      connect: vi.fn(),
      disconnect: vi.fn(),
    });

    render(<RealTimeProgressMonitor initialJob={mockRunningJob} />);
    
    expect(screen.getByText('Connection Issues')).toBeInTheDocument();
    expect(screen.getByText(/Unable to establish real-time connection/)).toBeInTheDocument();
    expect(screen.getByText('🔄 Try Again')).toBeInTheDocument();
  });
});