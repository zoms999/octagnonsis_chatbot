/**
 * Tests for progress bar components
 */

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProgressBar, CompactProgressBar } from '../progress-bar';
import { ETLJob } from '@/lib/types';

const mockJob: ETLJob = {
  job_id: 'test-job-123',
  status: 'running',
  progress: 65,
  current_step: 'Processing documents',
  estimated_completion_time: new Date(Date.now() + 300000).toISOString(), // 5 minutes from now
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('ProgressBar', () => {
  it('should render progress bar with job details', () => {
    render(<ProgressBar job={mockJob} />);
    
    expect(screen.getByText('Processing documents')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
    expect(screen.getByText(/ETA:/)).toBeInTheDocument();
  });

  it('should show correct status icon for running job', () => {
    render(<ProgressBar job={mockJob} />);
    
    expect(screen.getByText('🔄')).toBeInTheDocument();
  });

  it('should show completed status correctly', () => {
    const completedJob: ETLJob = {
      ...mockJob,
      status: 'completed',
      progress: 100,
    };
    
    render(<ProgressBar job={completedJob} />);
    
    expect(screen.getByText('✅')).toBeInTheDocument();
    expect(screen.getByText('✅ Job completed successfully')).toBeInTheDocument();
  });

  it('should show failed status with error message', () => {
    const failedJob: ETLJob = {
      ...mockJob,
      status: 'failed',
      progress: 45,
      error_message: 'Database connection failed',
    };
    
    render(<ProgressBar job={failedJob} />);
    
    expect(screen.getByText('❌')).toBeInTheDocument();
    expect(screen.getByText('Database connection failed')).toBeInTheDocument();
  });

  it('should handle different sizes', () => {
    const { rerender } = render(<ProgressBar job={mockJob} size="sm" />);
    
    // Check if small size classes are applied
    const progressBar = document.querySelector('.h-2');
    expect(progressBar).toBeInTheDocument();
    
    rerender(<ProgressBar job={mockJob} size="lg" />);
    
    // Check if large size classes are applied
    const largeProgressBar = document.querySelector('.h-4');
    expect(largeProgressBar).toBeInTheDocument();
  });

  it('should not show details when showDetails is false', () => {
    render(<ProgressBar job={mockJob} showDetails={false} />);
    
    expect(screen.queryByText('Processing documents')).not.toBeInTheDocument();
    expect(screen.queryByText('65%')).not.toBeInTheDocument();
  });

  it('should handle jobs without estimated completion time', () => {
    const jobWithoutETA: ETLJob = {
      ...mockJob,
      estimated_completion_time: undefined,
    };
    
    render(<ProgressBar job={jobWithoutETA} />);
    
    expect(screen.queryByText(/ETA:/)).not.toBeInTheDocument();
  });

  it('should clamp progress values to 0-100 range', () => {
    const jobWithInvalidProgress: ETLJob = {
      ...mockJob,
      progress: 150, // Invalid progress > 100
    };
    
    render(<ProgressBar job={jobWithInvalidProgress} />);
    
    expect(screen.getByText('100%')).toBeInTheDocument();
    
    const progressBar = document.querySelector('[style*="width: 100%"]');
    expect(progressBar).toBeInTheDocument();
  });
});

describe('CompactProgressBar', () => {
  it('should render compact progress bar', () => {
    render(<CompactProgressBar job={mockJob} />);
    
    expect(screen.getByText('65%')).toBeInTheDocument();
  });

  it('should hide percentage when showPercentage is false', () => {
    render(<CompactProgressBar job={mockJob} showPercentage={false} />);
    
    expect(screen.queryByText('65%')).not.toBeInTheDocument();
  });

  it('should show correct colors for different statuses', () => {
    const { rerender } = render(<CompactProgressBar job={mockJob} />);
    
    // Running job should have blue color
    let progressBar = document.querySelector('.bg-blue-600');
    expect(progressBar).toBeInTheDocument();
    
    // Completed job should have green color
    const completedJob: ETLJob = { ...mockJob, status: 'completed' };
    rerender(<CompactProgressBar job={completedJob} />);
    
    progressBar = document.querySelector('.bg-green-600');
    expect(progressBar).toBeInTheDocument();
    
    // Failed job should have red color
    const failedJob: ETLJob = { ...mockJob, status: 'failed' };
    rerender(<CompactProgressBar job={failedJob} />);
    
    progressBar = document.querySelector('.bg-red-600');
    expect(progressBar).toBeInTheDocument();
  });

  it('should handle zero progress', () => {
    const jobWithZeroProgress: ETLJob = {
      ...mockJob,
      progress: 0,
    };
    
    render(<CompactProgressBar job={jobWithZeroProgress} />);
    
    expect(screen.getByText('0%')).toBeInTheDocument();
    
    const progressBar = document.querySelector('[style*="width: 0%"]');
    expect(progressBar).toBeInTheDocument();
  });

  it('should handle negative progress values', () => {
    const jobWithNegativeProgress: ETLJob = {
      ...mockJob,
      progress: -10,
    };
    
    render(<CompactProgressBar job={jobWithNegativeProgress} />);
    
    expect(screen.getByText('0%')).toBeInTheDocument();
    
    const progressBar = document.querySelector('[style*="width: 0%"]');
    expect(progressBar).toBeInTheDocument();
  });
});