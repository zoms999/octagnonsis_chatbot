'use client';

import React, { useState } from 'react';
import { useETLJobStatus } from '@/hooks/api-hooks';
import { useETLActions } from '@/hooks/use-etl-actions';
import { ETLJob } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/loading';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { RealTimeProgressMonitor } from './real-time-progress-monitor';
import { formatDistanceToNow, format } from 'date-fns';

interface ETLJobDetailProps {
  job: ETLJob;
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

export function ETLJobDetail({ job }: ETLJobDetailProps) {
  const [currentJob, setCurrentJob] = React.useState<ETLJob>(job);
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

  // Use real-time job status polling as fallback for non-running jobs
  const {
    data: jobStatus,
    isLoading: isLoadingStatus,
    error: statusError,
  } = useETLJobStatus(job.job_id);

  // Update current job when job prop changes or when we get polling data
  React.useEffect(() => {
    if (jobStatus) {
      setCurrentJob(jobStatus);
    } else {
      setCurrentJob(job);
    }
  }, [job, jobStatus]);

  const statusColor = statusColors[currentJob.status];
  const statusIcon = statusIcons[currentJob.status];
  const isActiveJob = currentJob.status === 'running' || currentJob.status === 'pending';
  
  const jobCanRetry = canRetryJob(currentJob);
  const jobCanCancel = canCancelJob(currentJob);
  const isJobRetrying = isRetrying(currentJob.job_id);
  const isJobCancelling = isCancelling(currentJob.job_id);

  const handleJobUpdate = (updatedJob: ETLJob) => {
    setCurrentJob(updatedJob);
  };

  const handleRetryConfirm = () => {
    retryJob(currentJob.job_id);
    setShowRetryDialog(false);
  };

  const handleCancelConfirm = () => {
    cancelJob(currentJob.job_id);
    setShowCancelDialog(false);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Job Details</h3>
          <p className="text-sm text-gray-600 font-mono">{currentJob.job_id}</p>
        </div>
        
        {/* Status Badge */}
        <span className={`
          inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border
          ${statusColor}
        `}>
          <span className="mr-2">{statusIcon}</span>
          {currentJob.status.charAt(0).toUpperCase() + currentJob.status.slice(1)}
          {isLoadingStatus && currentJob.status === 'running' && (
            <Spinner size="sm" className="ml-2" />
          )}
        </span>
      </div>

      {/* Real-time Progress Monitor for Active Jobs */}
      {isActiveJob ? (
        <RealTimeProgressMonitor
          initialJob={currentJob}
          onJobUpdate={handleJobUpdate}
          autoConnect={true}
        />
      ) : (
        <>
          {/* Current Step for Completed/Failed Jobs */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Final Step</h4>
            <p className="text-gray-900 bg-gray-50 p-3 rounded border">
              {currentJob.current_step || 'No step information available'}
            </p>
          </div>

          {/* Final Progress for Completed Jobs */}
          {currentJob.status === 'completed' && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-700">Final Progress</h4>
                <span className="text-sm text-gray-600">100%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div className="bg-green-600 h-3 rounded-full w-full" />
              </div>
            </div>
          )}
        </>
      )}

      {/* Error Message */}
      {currentJob.status === 'failed' && currentJob.error_message && (
        <div>
          <h4 className="text-sm font-medium text-red-700 mb-2">Error Details</h4>
          <div className="bg-red-50 border border-red-200 rounded p-3">
            <p className="text-sm text-red-800">{currentJob.error_message}</p>
          </div>
        </div>
      )}

      {/* Timestamps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-1">Created</h4>
          <p className="text-sm text-gray-600">
            {format(new Date(currentJob.created_at), 'PPpp')}
          </p>
          <p className="text-xs text-gray-500">
            {formatDistanceToNow(new Date(currentJob.created_at), { addSuffix: true })}
          </p>
        </div>
        
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-1">Last Updated</h4>
          <p className="text-sm text-gray-600">
            {format(new Date(currentJob.updated_at), 'PPpp')}
          </p>
          <p className="text-xs text-gray-500">
            {formatDistanceToNow(new Date(currentJob.updated_at), { addSuffix: true })}
          </p>
        </div>
      </div>

      {/* Actions */}
      {(jobCanRetry || jobCanCancel) && (
        <div className="flex items-center space-x-3 pt-4 border-t">
          {jobCanRetry && (
            <Button
              onClick={() => setShowRetryDialog(true)}
              disabled={isJobRetrying}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isJobRetrying ? (
                <>
                  <Spinner size="sm" className="mr-2" />
                  Retrying...
                </>
              ) : (
                <>
                  🔄 Retry Job
                </>
              )}
            </Button>
          )}
          
          {jobCanCancel && (
            <Button
              variant="outline"
              onClick={() => setShowCancelDialog(true)}
              disabled={isJobCancelling}
              className="text-red-600 border-red-300 hover:bg-red-50"
            >
              {isJobCancelling ? (
                <>
                  <Spinner size="sm" className="mr-2" />
                  Cancelling...
                </>
              ) : (
                <>
                  ⏹️ Cancel Job
                </>
              )}
            </Button>
          )}
        </div>
      )}

      {/* Status Error */}
      {statusError && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
          <p className="text-sm text-yellow-800">
            ⚠️ Unable to fetch real-time status updates. Showing last known status.
          </p>
        </div>
      )}

      {/* Confirmation Dialogs */}
      <ConfirmationDialog
        isOpen={showRetryDialog}
        onClose={() => setShowRetryDialog(false)}
        onConfirm={handleRetryConfirm}
        title="Retry ETL Job"
        message={`Are you sure you want to retry job ${currentJob.job_id.slice(0, 8)}...? This will create a new job instance and restart the processing from the beginning.`}
        confirmText="Retry Job"
        variant="default"
        isLoading={isJobRetrying}
      />

      <ConfirmationDialog
        isOpen={showCancelDialog}
        onClose={() => setShowCancelDialog(false)}
        onConfirm={handleCancelConfirm}
        title="Cancel ETL Job"
        message={`Are you sure you want to cancel job ${currentJob.job_id.slice(0, 8)}...? This action cannot be undone and will stop the current processing.`}
        confirmText="Cancel Job"
        cancelText="Keep Running"
        variant="destructive"
        isLoading={isJobCancelling}
      />
    </div>
  );
}