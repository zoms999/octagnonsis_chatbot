'use client';

import { useState } from 'react';
import { useRetryETLJob, useCancelETLJob, useTriggerReprocessing } from './api-hooks';
import { useToast } from '@/components/ui/toast';
import { ETLJob } from '@/lib/types';

interface ETLActionsState {
  retryingJobs: Set<string>;
  cancellingJobs: Set<string>;
  reprocessingUsers: Set<string>;
}

export function useETLActions() {
  const [state, setState] = useState<ETLActionsState>({
    retryingJobs: new Set(),
    cancellingJobs: new Set(),
    reprocessingUsers: new Set(),
  });

  const { toast } = useToast();

  // Retry job mutation
  const retryMutation = useRetryETLJob({
    onSuccess: (data, jobId) => {
      setState(prev => ({
        ...prev,
        retryingJobs: new Set(Array.from(prev.retryingJobs).filter(id => id !== jobId)),
      }));
      
      toast.success(
        'Job Retry Started',
        `Job ${jobId.slice(0, 8)}... has been queued for retry.`
      );
    },
    onError: (error, jobId) => {
      setState(prev => ({
        ...prev,
        retryingJobs: new Set(Array.from(prev.retryingJobs).filter(id => id !== jobId)),
      }));
      
      toast.error(
        'Retry Failed',
        error.message || 'Failed to retry the job. Please try again.'
      );
    },
  });

  // Cancel job mutation
  const cancelMutation = useCancelETLJob({
    onSuccess: (data, jobId) => {
      setState(prev => ({
        ...prev,
        cancellingJobs: new Set(Array.from(prev.cancellingJobs).filter(id => id !== jobId)),
      }));
      
      toast.success(
        'Job Cancelled',
        `Job ${jobId.slice(0, 8)}... has been cancelled successfully.`
      );
    },
    onError: (error, jobId) => {
      setState(prev => ({
        ...prev,
        cancellingJobs: new Set(Array.from(prev.cancellingJobs).filter(id => id !== jobId)),
      }));
      
      toast.error(
        'Cancellation Failed',
        error.message || 'Failed to cancel the job. Please try again.'
      );
    },
  });

  // Reprocessing mutation
  const reprocessMutation = useTriggerReprocessing({
    onSuccess: (data, { userId }) => {
      setState(prev => ({
        ...prev,
        reprocessingUsers: new Set(Array.from(prev.reprocessingUsers).filter(id => id !== userId)),
      }));
      
      toast.success(
        'Reprocessing Started',
        'Document reprocessing has been initiated. You can monitor progress in the ETL jobs list.'
      );
    },
    onError: (error, { userId }) => {
      setState(prev => ({
        ...prev,
        reprocessingUsers: new Set(Array.from(prev.reprocessingUsers).filter(id => id !== userId)),
      }));
      
      toast.error(
        'Reprocessing Failed',
        error.message || 'Failed to start reprocessing. Please try again.'
      );
    },
  });

  // Action handlers
  const retryJob = (jobId: string) => {
    setState(prev => ({
      ...prev,
      retryingJobs: new Set([...Array.from(prev.retryingJobs), jobId]),
    }));
    
    retryMutation.mutate(jobId);
  };

  const cancelJob = (jobId: string) => {
    setState(prev => ({
      ...prev,
      cancellingJobs: new Set([...Array.from(prev.cancellingJobs), jobId]),
    }));
    
    cancelMutation.mutate(jobId);
  };

  const triggerReprocessing = (userId: string, force: boolean = false) => {
    setState(prev => ({
      ...prev,
      reprocessingUsers: new Set([...Array.from(prev.reprocessingUsers), userId]),
    }));
    
    reprocessMutation.mutate({ userId, force });
  };

  // Status checkers
  const isRetrying = (jobId: string) => state.retryingJobs.has(jobId);
  const isCancelling = (jobId: string) => state.cancellingJobs.has(jobId);
  const isReprocessing = (userId: string) => state.reprocessingUsers.has(userId);

  // Job action availability
  const canRetryJob = (job: ETLJob) => {
    return (job.status === 'failed' || job.status === 'cancelled') && !isRetrying(job.job_id);
  };

  const canCancelJob = (job: ETLJob) => {
    return (job.status === 'running' || job.status === 'pending') && !isCancelling(job.job_id);
  };

  return {
    // Actions
    retryJob,
    cancelJob,
    triggerReprocessing,
    
    // Status
    isRetrying,
    isCancelling,
    isReprocessing,
    
    // Availability
    canRetryJob,
    canCancelJob,
    
    // Loading states
    isAnyActionLoading: state.retryingJobs.size > 0 || state.cancellingJobs.size > 0 || state.reprocessingUsers.size > 0,
  };
}