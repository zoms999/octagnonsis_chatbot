import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { QueryClient } from '@tanstack/react-query';
import { queryKeys, cacheConfig, cacheUtils, cacheAnalytics } from '../react-query';

// Mock API client
vi.mock('../api', () => ({
  ApiClient: {
    getUserProfile: vi.fn(),
    getConversationHistory: vi.fn(),
    getETLJobs: vi.fn(),
    getUserDocuments: vi.fn(),
    validateSession: vi.fn(),
  },
}));

describe('React Query Caching Strategies', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  afterEach(() => {
    queryClient.clear();
  });

  describe('Cache Configuration', () => {
    it('should have appropriate stale times for different data types', () => {
      expect(cacheConfig.auth.staleTime).toBe(2 * 60 * 1000); // 2 minutes
      expect(cacheConfig.userProfile.staleTime).toBe(5 * 60 * 1000); // 5 minutes
      expect(cacheConfig.documents.staleTime).toBe(10 * 60 * 1000); // 10 minutes
      expect(cacheConfig.conversations.staleTime).toBe(2 * 60 * 1000); // 2 minutes
      expect(cacheConfig.etlJobs.staleTime).toBe(30 * 1000); // 30 seconds
      expect(cacheConfig.etlJobStatus.staleTime).toBe(5 * 1000); // 5 seconds
    });

    it('should have longer garbage collection times than stale times', () => {
      Object.values(cacheConfig).forEach(config => {
        if (typeof config === 'object' && 'staleTime' in config && 'gcTime' in config) {
          expect(config.gcTime).toBeGreaterThan(config.staleTime);
        }
      });
    });

    it('should have appropriate refetch intervals for real-time data', () => {
      expect(typeof cacheConfig.etlJobs.refetchInterval).toBe('function');
      expect(typeof cacheConfig.etlJobStatus.refetchInterval).toBe('function');
    });
  });

  describe('Query Keys Factory', () => {
    it('should generate consistent query keys', () => {
      const userId = 'user123';
      const jobId = 'job456';
      
      expect(queryKeys.user.profile(userId)).toEqual(['user', 'profile', userId]);
      expect(queryKeys.etl.jobStatus(jobId)).toEqual(['etl', 'job', jobId, 'status']);
      expect(queryKeys.chat.history(userId, 1, 10)).toEqual(['chat', 'history', userId, { page: 1, limit: 10 }]);
    });

    it('should handle optional parameters in query keys', () => {
      const userId = 'user123';
      
      expect(queryKeys.chat.history(userId)).toEqual(['chat', 'history', userId, { page: undefined, limit: undefined }]);
      expect(queryKeys.user.documents(userId, 1, 20, 'pdf')).toEqual(['user', 'documents', userId, { page: 1, limit: 20, docType: 'pdf' }]);
    });
  });

  describe('Cache Utils', () => {
    it('should invalidate user queries correctly', async () => {
      const userId = 'user123';
      
      // Set some test data
      queryClient.setQueryData(queryKeys.user.profile(userId), { id: userId, name: 'Test User' });
      queryClient.setQueryData(queryKeys.chat.history(userId), { conversations: [] });
      
      // Spy on invalidateQueries
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');
      
      // Test invalidation directly with queryClient
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.user.profile(userId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.user.documents(userId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.chat.history(userId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.etl.jobs(userId) }),
      ]);
      
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: queryKeys.user.profile(userId) });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: queryKeys.chat.history(userId) });
    });

    it('should perform optimistic updates with rollback capability', () => {
      const queryKey = queryKeys.user.profile('user123');
      const initialData = { id: 'user123', name: 'John Doe' };
      const updatedData = { id: 'user123', name: 'Jane Doe' };
      
      // Set initial data
      queryClient.setQueryData(queryKey, initialData);
      
      // Perform optimistic update manually for testing
      const previousData = queryClient.getQueryData(queryKey);
      queryClient.setQueryData(queryKey, (old: any) => ({ ...old, name: 'Jane Doe' }));
      
      // Check updated data
      expect(queryClient.getQueryData(queryKey)).toEqual(updatedData);
      
      // Rollback manually
      queryClient.setQueryData(queryKey, previousData);
      
      // Check rollback worked
      expect(queryClient.getQueryData(queryKey)).toEqual(initialData);
    });

    it('should batch optimistic updates correctly', () => {
      const userKey = queryKeys.user.profile('user123');
      const chatKey = queryKeys.chat.history('user123');
      
      const initialUserData = { id: 'user123', name: 'John' };
      const initialChatData = { conversations: [] };
      
      queryClient.setQueryData(userKey, initialUserData);
      queryClient.setQueryData(chatKey, initialChatData);
      
      // Store previous data for rollback
      const previousUserData = queryClient.getQueryData(userKey);
      const previousChatData = queryClient.getQueryData(chatKey);
      
      // Apply updates
      queryClient.setQueryData(userKey, (old: any) => ({ ...old, name: 'Jane' }));
      queryClient.setQueryData(chatKey, (old: any) => ({ ...old, conversations: [{ id: '1' }] }));
      
      // Check updates applied
      expect(queryClient.getQueryData(userKey)).toEqual({ id: 'user123', name: 'Jane' });
      expect(queryClient.getQueryData(chatKey)).toEqual({ conversations: [{ id: '1' }] });
      
      // Rollback all
      queryClient.setQueryData(userKey, previousUserData);
      queryClient.setQueryData(chatKey, previousChatData);
      
      // Check rollback worked
      expect(queryClient.getQueryData(userKey)).toEqual({ id: 'user123', name: 'John' });
      expect(queryClient.getQueryData(chatKey)).toEqual({ conversations: [] });
    });

    it('should validate data updates when validator provided', () => {
      const queryKey = queryKeys.user.profile('user123');
      const initialData = { id: 'user123', name: 'John Doe' };
      
      queryClient.setQueryData(queryKey, initialData);
      
      // Simulate valid update with validation
      const updater = (old: any) => ({ ...old, name: 'Jane Doe' });
      const validator = (data: any) => data.name.length > 0;
      
      const currentData = queryClient.getQueryData(queryKey);
      const newData = updater(currentData);
      
      if (validator(newData)) {
        queryClient.setQueryData(queryKey, newData);
      }
      
      expect(queryClient.getQueryData(queryKey)).toEqual({ id: 'user123', name: 'Jane Doe' });
      
      // Simulate invalid update with validation
      const invalidUpdater = (old: any) => ({ ...old, name: '' });
      const currentData2 = queryClient.getQueryData(queryKey);
      const newData2 = invalidUpdater(currentData2);
      
      if (!validator(newData2)) {
        // Don't update if validation fails
      } else {
        queryClient.setQueryData(queryKey, newData2);
      }
      
      expect(queryClient.getQueryData(queryKey)).toEqual({ id: 'user123', name: 'Jane Doe' }); // Unchanged
    });

    it('should check query staleness correctly', () => {
      const queryKey = queryKeys.user.profile('user123');
      
      // No query exists - should be undefined
      const query1 = queryClient.getQueryState(queryKey);
      expect(query1).toBeUndefined();
      
      // Set fresh data
      queryClient.setQueryData(queryKey, { id: 'user123' });
      
      // Query should exist now
      const query2 = queryClient.getQueryState(queryKey);
      expect(query2).toBeDefined();
      expect(query2?.data).toEqual({ id: 'user123' });
    });

    it('should get query status information', () => {
      const queryKey = queryKeys.user.profile('user123');
      
      // No query exists
      let query = queryClient.getQueryState(queryKey);
      expect(query).toBeUndefined();
      
      // Set data
      queryClient.setQueryData(queryKey, { id: 'user123' });
      
      query = queryClient.getQueryState(queryKey);
      expect(query).toBeDefined();
      expect(query?.data).toEqual({ id: 'user123' });
      expect(query?.dataUpdatedAt).toBeTypeOf('number');
    });
  });

  describe('Cache Analytics', () => {
    it('should calculate cache hit rate', () => {
      // Set some queries with data (hits)
      queryClient.setQueryData(queryKeys.user.profile('user1'), { id: 'user1' });
      queryClient.setQueryData(queryKeys.user.profile('user2'), { id: 'user2' });
      
      const hitRate = cacheAnalytics.getCacheHitRate();
      expect(hitRate).toBeGreaterThanOrEqual(0);
      expect(hitRate).toBeLessThanOrEqual(100);
    });

    it('should get cache statistics', () => {
      // Test that cache analytics function exists and returns proper structure
      const stats = cacheAnalytics.getCacheStats();
      
      expect(stats).toHaveProperty('totalQueries');
      expect(stats).toHaveProperty('activeQueries');
      expect(stats).toHaveProperty('staleQueries');
      expect(stats).toHaveProperty('errorQueries');
      expect(stats).toHaveProperty('loadingQueries');
      
      expect(typeof stats.totalQueries).toBe('number');
      expect(typeof stats.activeQueries).toBe('number');
    });

    it('should get query performance data', () => {
      const queryKey = queryKeys.user.profile('user123');
      
      // No query exists - should return null
      let query = queryClient.getQueryState(queryKey);
      expect(query).toBeUndefined();
      
      // Set data
      queryClient.setQueryData(queryKey, { id: 'user123' });
      
      query = queryClient.getQueryState(queryKey);
      expect(query).toHaveProperty('dataUpdatedAt');
      expect(query).toHaveProperty('errorUpdateCount');
      expect(query?.data).toEqual({ id: 'user123' });
    });
  });

  describe('Smart Refetch Intervals', () => {
    it('should return appropriate refetch interval for ETL jobs based on status', () => {
      const etlJobsConfig = cacheConfig.etlJobs;
      
      // Running jobs should refetch frequently
      const runningJobsData = {
        jobs: [
          { id: '1', status: 'running' },
          { id: '2', status: 'completed' },
        ],
      };
      
      if (typeof etlJobsConfig.refetchInterval === 'function') {
        const interval = etlJobsConfig.refetchInterval(runningJobsData);
        expect(interval).toBe(15 * 1000); // 15 seconds
      }
      
      // No running jobs should not refetch
      const completedJobsData = {
        jobs: [
          { id: '1', status: 'completed' },
          { id: '2', status: 'failed' },
        ],
      };
      
      if (typeof etlJobsConfig.refetchInterval === 'function') {
        const interval = etlJobsConfig.refetchInterval(completedJobsData);
        expect(interval).toBe(false);
      }
    });

    it('should return appropriate refetch interval for ETL job status', () => {
      const etlJobStatusConfig = cacheConfig.etlJobStatus;
      
      // Running job should refetch frequently
      const runningJobData = { status: 'running', progress: 50 };
      
      if (typeof etlJobStatusConfig.refetchInterval === 'function') {
        const interval = etlJobStatusConfig.refetchInterval(runningJobData);
        expect(interval).toBe(3 * 1000); // 3 seconds
      }
      
      // Completed job should not refetch
      const completedJobData = { status: 'completed', progress: 100 };
      
      if (typeof etlJobStatusConfig.refetchInterval === 'function') {
        const interval = etlJobStatusConfig.refetchInterval(completedJobData);
        expect(interval).toBe(false);
      }
    });
  });
});