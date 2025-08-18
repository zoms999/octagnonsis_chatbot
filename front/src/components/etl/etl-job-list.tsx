'use client';

import React, { useState } from 'react';
import { useETLJobs } from '@/hooks/api-hooks';
import { useAuth } from '@/providers/auth-provider';
import { useETLActions } from '@/hooks/use-etl-actions';
import { ETLJob } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/loading';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { CompactProgressBar } from './progress-bar';
import { useETLProgress } from '@/hooks/use-etl-progress';
import { formatDistanceToNow } from 'date-fns';

interface ETLJobListProps {
  onJobSelect?: (job: ETLJob) => void;
  selectedJobId?: string;
}

const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  running: 'bg-blue-100 text-blue-800 border-blue-200',
  completed: 'bg-green-100 text-green-800 border-green-200',
  failed: 'bg-red-100 text-red-800 border-red-200',
  cancelled: 'bg-gray-100 text-gray-800 border-gray-200',
};

const statusIcons = {
  pending: '⏳',
  running: '🔄',
  completed: '✅',
  failed: '❌',
  cancelled: '⏹️',
};

export function ETLJobList({ onJobSelect, selectedJobId }: ETLJobListProps) {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const limit = 10;

  const {
    data: jobsResponse,
    isLoading,
    error,
    refetch,
  } = useETLJobs(user?.id || '', page, limit);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Spinner size="lg" />
        <span className="ml-2 text-gray-600">Loading ETL jobs...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-red-800">Failed to load ETL jobs</h3>
            <p className="text-sm text-red-600 mt-1">
              {error.message || 'An error occurred while loading jobs'}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="text-red-700 border-red-300 hover:bg-red-50"
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const jobs = jobsResponse?.jobs || [];
  const totalJobs = jobsResponse?.total || 0;
  const totalPages = Math.ceil(totalJobs / limit);

  if (jobs.length === 0) {
    return (
      <div className="text-center p-8 bg-gray-50 rounded-lg">
        <div className="text-gray-400 text-4xl mb-4">📋</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No ETL jobs found</h3>
        <p className="text-gray-600">
          No processing jobs have been created for your account yet.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          ETL Jobs ({totalJobs})
        </h2>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          className="text-gray-600"
        >
          🔄 Refresh
        </Button>
      </div>

      {/* Job List */}
      <div className="space-y-2">
        {jobs.map((job) => (
          <JobCard
            key={job.job_id}
            job={job}
            isSelected={selectedJobId === job.job_id}
            onClick={() => onJobSelect?.(job)}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="text-sm text-gray-600">
            Page {page} of {totalPages} ({totalJobs} total jobs)
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

interface JobCardProps {
  job: ETLJob;
  isSelected: boolean;
  onClick: () => void;
}

interface JobActionsProps {
  job: ETLJob;
}

function JobActions({ job }: JobActionsProps) {
  const [showRetryDialog, setShowRetryDialog] = useState(false);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  
  const {
    retryJob,
    cancelJob,
    isRetrying,
    isCancelling,
    canRetryJob,
    canCancelJob,
  } = useETLActions();

  const jobCanRetry = canRetryJob(job);
  const jobCanCancel = canCancelJob(job);
  const isJobRetrying = isRetrying(job.job_id);
  const isJobCancelling = isCancelling(job.job_id);

  const handleRetryConfirm = () => {
    retryJob(job.job_id);
    setShowRetryDialog(false);
  };

  const handleCancelConfirm = () => {
    cancelJob(job.job_id);
    setShowCancelDialog(false);
  };

  const handleActionClick = (e: React.MouseEvent, action: () => void) => {
    e.stopPropagation(); // Prevent card selection
    action();
  };

  if (!jobCanRetry && !jobCanCancel) {
    return null;
  }

  return (
    <>
      <div className="flex items-center space-x-2">
        {jobCanRetry && (
          <Button
            size="sm"
            variant="outline"
            onClick={(e) => handleActionClick(e, () => setShowRetryDialog(true))}
            disabled={isJobRetrying}
            className="text-blue-600 border-blue-300 hover:bg-blue-50"
          >
            {isJobRetrying ? '⏳' : '🔄'}
          </Button>
        )}
        
        {jobCanCancel && (
          <Button
            size="sm"
            variant="outline"
            onClick={(e) => handleActionClick(e, () => setShowCancelDialog(true))}
            disabled={isJobCancelling}
            className="text-red-600 border-red-300 hover:bg-red-50"
          >
            {isJobCancelling ? '⏳' : '⏹️'}
          </Button>
        )}
      </div>

      {/* Confirmation Dialogs */}
      <ConfirmationDialog
        isOpen={showRetryDialog}
        onClose={() => setShowRetryDialog(false)}
        onConfirm={handleRetryConfirm}
        title="Retry ETL Job"
        message={`Retry job ${job.job_id.slice(0, 8)}...?`}
        confirmText="Retry"
        variant="default"
        isLoading={isJobRetrying}
      />

      <ConfirmationDialog
        isOpen={showCancelDialog}
        onClose={() => setShowCancelDialog(false)}
        onConfirm={handleCancelConfirm}
        title="Cancel ETL Job"
        message={`Cancel job ${job.job_id.slice(0, 8)}...?`}
        confirmText="Cancel Job"
        variant="destructive"
        isLoading={isJobCancelling}
      />
    </>
  );
}

function JobCard({ job, isSelected, onClick }: JobCardProps) {
  const statusColor = statusColors[job.status];
  const statusIcon = statusIcons[job.status];
  
  // Use real-time progress monitoring for active jobs
  const { currentJob, isConnected } = useETLProgress(job, {
    autoConnect: job.status === 'running' || job.status === 'pending',
  });

  // Use the updated job data from SSE if available
  const displayJob = currentJob;

  return (
    <div
      className={`
        p-4 border rounded-lg cursor-pointer transition-all duration-200
        ${isSelected 
          ? 'border-blue-500 bg-blue-50 shadow-md' 
          : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
        }
      `}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          {/* Job ID and Status */}
          <div className="flex items-center space-x-3 mb-2">
            <span className="font-mono text-sm text-gray-600">
              {displayJob.job_id.slice(0, 8)}...
            </span>
            <span className={`
              inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border
              ${statusColors[displayJob.status]}
            `}>
              <span className="mr-1">{statusIcons[displayJob.status]}</span>
              {displayJob.status.charAt(0).toUpperCase() + displayJob.status.slice(1)}
            </span>
            {/* Real-time connection indicator */}
            {isConnected && (displayJob.status === 'running' || displayJob.status === 'pending') && (
              <div className="flex items-center space-x-1 text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-xs font-medium">Live</span>
              </div>
            )}
          </div>

          {/* Current Step */}
          <div className="mb-2">
            <p className="text-sm text-gray-900 font-medium">
              {displayJob.current_step || 'Initializing...'}
            </p>
          </div>

          {/* Compact Progress Bar */}
          {(displayJob.status === 'running' || displayJob.status === 'pending' || displayJob.status === 'completed') && (
            <div className="mb-2">
              <CompactProgressBar job={displayJob} showPercentage={true} />
            </div>
          )}

          {/* Error Message */}
          {displayJob.status === 'failed' && displayJob.error_message && (
            <div className="mb-2">
              <p className="text-sm text-red-600 bg-red-50 p-2 rounded border">
                {displayJob.error_message}
              </p>
            </div>
          )}

          {/* Timestamps */}
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>
              Created {formatDistanceToNow(new Date(displayJob.created_at), { addSuffix: true })}
            </span>
            {displayJob.estimated_completion_time && (displayJob.status === 'running' || displayJob.status === 'pending') && (
              <span>
                ETA: {formatDistanceToNow(new Date(displayJob.estimated_completion_time), { addSuffix: true })}
              </span>
            )}
          </div>
        </div>

        {/* Actions and Selection */}
        <div className="ml-4 flex items-center space-x-2">
          <JobActions job={displayJob} />
          
          {isSelected && (
            <div className="text-blue-600">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}