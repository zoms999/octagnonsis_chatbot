'use client';

import React from 'react';
import { ETLJob } from '@/lib/types';
import { formatDistanceToNow } from 'date-fns';

interface ProgressBarProps {
  job: ETLJob;
  showDetails?: boolean;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
}

const sizeClasses = {
  sm: 'h-2',
  md: 'h-3',
  lg: 'h-4',
};

const textSizeClasses = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-base',
};

export function ProgressBar({ 
  job, 
  showDetails = true, 
  size = 'md',
  animated = true 
}: ProgressBarProps) {
  const progress = Math.max(0, Math.min(100, job.progress));
  const isActive = job.status === 'running' || job.status === 'pending';
  
  const getProgressColor = () => {
    switch (job.status) {
      case 'completed':
        return 'bg-green-600';
      case 'failed':
        return 'bg-red-600';
      case 'cancelled':
        return 'bg-gray-600';
      case 'running':
        return 'bg-blue-600';
      case 'pending':
        return 'bg-yellow-600';
      default:
        return 'bg-gray-600';
    }
  };

  const getStatusIcon = () => {
    switch (job.status) {
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      case 'cancelled':
        return '⏹️';
      case 'running':
        return '🔄';
      case 'pending':
        return '⏳';
      default:
        return '❓';
    }
  };

  return (
    <div className="space-y-2">
      {/* Progress Header */}
      {showDetails && (
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-lg">{getStatusIcon()}</span>
            <span className={`font-medium text-gray-900 ${textSizeClasses[size]}`}>
              {job.current_step || 'Initializing...'}
            </span>
          </div>
          <span className={`font-semibold text-gray-700 ${textSizeClasses[size]}`}>
            {Math.round(progress)}%
          </span>
        </div>
      )}

      {/* Progress Bar */}
      <div className="relative">
        <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${sizeClasses[size]}`}>
          <div
            className={`
              ${sizeClasses[size]} rounded-full transition-all duration-500 ease-out
              ${getProgressColor()}
              ${animated && isActive ? 'animate-pulse' : ''}
            `}
            style={{ width: `${progress}%` }}
          />
          
          {/* Animated stripe effect for running jobs */}
          {animated && isActive && (
            <div
              className={`
                absolute top-0 left-0 ${sizeClasses[size]} rounded-full
                bg-gradient-to-r from-transparent via-white to-transparent
                opacity-30 animate-pulse
              `}
              style={{ width: `${progress}%` }}
            />
          )}
        </div>
      </div>

      {/* Additional Details */}
      {showDetails && (
        <div className="space-y-1">
          {/* Estimated Completion Time */}
          {job.estimated_completion_time && isActive && (
            <div className={`text-gray-600 ${textSizeClasses[size]}`}>
              <span className="font-medium">ETA:</span>{' '}
              {formatDistanceToNow(new Date(job.estimated_completion_time), { addSuffix: true })}
            </div>
          )}

          {/* Error Message */}
          {job.status === 'failed' && job.error_message && (
            <div className={`text-red-600 bg-red-50 p-2 rounded border ${textSizeClasses[size]}`}>
              <span className="font-medium">Error:</span> {job.error_message}
            </div>
          )}

          {/* Status Message */}
          {job.status === 'completed' && (
            <div className={`text-green-600 ${textSizeClasses[size]}`}>
              ✅ Job completed successfully
            </div>
          )}

          {job.status === 'cancelled' && (
            <div className={`text-gray-600 ${textSizeClasses[size]}`}>
              ⏹️ Job was cancelled
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Compact progress indicator for use in lists or small spaces
 */
export function CompactProgressBar({ job, showPercentage = true }: { 
  job: ETLJob; 
  showPercentage?: boolean; 
}) {
  const progress = Math.max(0, Math.min(100, job.progress));
  
  return (
    <div className="flex items-center space-x-2">
      <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`
            h-2 rounded-full transition-all duration-300
            ${job.status === 'completed' ? 'bg-green-600' : 
              job.status === 'failed' ? 'bg-red-600' :
              job.status === 'cancelled' ? 'bg-gray-600' :
              'bg-blue-600'}
          `}
          style={{ width: `${progress}%` }}
        />
      </div>
      {showPercentage && (
        <span className="text-xs text-gray-600 font-medium min-w-[3rem] text-right">
          {Math.round(progress)}%
        </span>
      )}
    </div>
  );
}