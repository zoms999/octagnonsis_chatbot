'use client';

import React, { useState, Suspense } from 'react';
import { LazyETLComponents } from '@/components/lazy';
import { ETLJobStats } from '@/components/etl/etl-job-stats';
import { ReprocessingTrigger } from '@/components/etl/reprocessing-trigger';
import { useAuth } from '@/providers/auth-provider';
import { useETLJobs } from '@/hooks/api-hooks';
import { ETLJob } from '@/lib/types';
import { LoadingFallbacks } from '@/lib/lazy-loading';

// Lazy load heavy components
const { ETLJobList, ETLJobDetail } = LazyETLComponents;

export default function ETLPage() {
  const { user } = useAuth();
  const [selectedJob, setSelectedJob] = useState<ETLJob | null>(null);

  // Fetch jobs data for stats
  const { data: jobsResponse } = useETLJobs(user?.id || '', 1, 100); // Get more jobs for stats
  const jobs = jobsResponse?.jobs || [];

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">ETL Job Monitoring</h1>
          <p className="text-gray-600 mt-2">
            Monitor and manage your data processing jobs in real-time.
          </p>
        </div>
        
        {/* Reprocessing Actions */}
        <ReprocessingTrigger />
      </div>

      {/* Job Statistics */}
      <ETLJobStats jobs={jobs} />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Job List */}
        <div className="lg:col-span-2">
          <Suspense fallback={<LoadingFallbacks.Component />}>
            <ETLJobList
              onJobSelect={setSelectedJob}
              selectedJobId={selectedJob?.job_id}
            />
          </Suspense>
        </div>

        {/* Job Detail Panel */}
        <div>
          {selectedJob ? (
            <Suspense fallback={<LoadingFallbacks.Component />}>
              <ETLJobDetail job={selectedJob} />
            </Suspense>
          ) : (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
              <div className="text-gray-400 text-4xl mb-4">📋</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Job</h3>
              <p className="text-gray-600">
                Choose a job from the list to view detailed information and available actions.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}