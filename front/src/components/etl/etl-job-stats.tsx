'use client';

import React from 'react';
import { ETLJob } from '@/lib/types';

interface ETLJobStatsProps {
  jobs: ETLJob[];
}

export function ETLJobStats({ jobs }: ETLJobStatsProps) {
  const stats = React.useMemo(() => {
    const total = jobs.length;
    const pending = jobs.filter(job => job.status === 'pending').length;
    const running = jobs.filter(job => job.status === 'running').length;
    const completed = jobs.filter(job => job.status === 'completed').length;
    const failed = jobs.filter(job => job.status === 'failed').length;
    const cancelled = jobs.filter(job => job.status === 'cancelled').length;

    const successRate = total > 0 ? Math.round((completed / total) * 100) : 0;
    const activeJobs = pending + running;

    return {
      total,
      pending,
      running,
      completed,
      failed,
      cancelled,
      successRate,
      activeJobs,
    };
  }, [jobs]);

  const statCards = [
    {
      label: 'Total Jobs',
      value: stats.total,
      icon: '📋',
      color: 'text-gray-600',
      bgColor: 'bg-gray-50',
    },
    {
      label: 'Active Jobs',
      value: stats.activeJobs,
      icon: '🔄',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: 'Completed',
      value: stats.completed,
      icon: '✅',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      label: 'Failed',
      value: stats.failed,
      icon: '❌',
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    },
  ];

  return (
    <div className="space-y-4">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <div
            key={stat.label}
            className={`${stat.bgColor} rounded-lg p-4 border border-gray-200`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{stat.label}</p>
                <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
              </div>
              <div className="text-2xl">{stat.icon}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Success Rate */}
      {stats.total > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-gray-700">Success Rate</h4>
            <span className="text-sm font-semibold text-gray-900">{stats.successRate}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                stats.successRate >= 80 
                  ? 'bg-green-500' 
                  : stats.successRate >= 60 
                  ? 'bg-yellow-500' 
                  : 'bg-red-500'
              }`}
              style={{ width: `${stats.successRate}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>{stats.completed} completed</span>
            <span>{stats.failed} failed</span>
          </div>
        </div>
      )}

      {/* Status Breakdown */}
      {stats.total > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Status Breakdown</h4>
          <div className="space-y-2">
            {stats.pending > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center">
                  <span className="w-3 h-3 bg-yellow-400 rounded-full mr-2"></span>
                  Pending
                </span>
                <span className="font-medium">{stats.pending}</span>
              </div>
            )}
            {stats.running > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center">
                  <span className="w-3 h-3 bg-blue-400 rounded-full mr-2"></span>
                  Running
                </span>
                <span className="font-medium">{stats.running}</span>
              </div>
            )}
            {stats.completed > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center">
                  <span className="w-3 h-3 bg-green-400 rounded-full mr-2"></span>
                  Completed
                </span>
                <span className="font-medium">{stats.completed}</span>
              </div>
            )}
            {stats.failed > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center">
                  <span className="w-3 h-3 bg-red-400 rounded-full mr-2"></span>
                  Failed
                </span>
                <span className="font-medium">{stats.failed}</span>
              </div>
            )}
            {stats.cancelled > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center">
                  <span className="w-3 h-3 bg-gray-400 rounded-full mr-2"></span>
                  Cancelled
                </span>
                <span className="font-medium">{stats.cancelled}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}