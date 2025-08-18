import { QueryClient, DefaultOptions, MutationCache, QueryCache } from '@tanstack/react-query';
import { ApiErrorHandler } from './api';
import { ApiError } from './types';
import { ErrorHandler } from './error-handling';

// React Query configuration with caching strategies
const queryConfig: DefaultOptions = {
  queries: {
    // Global query defaults
    staleTime: 5 * 60 * 1000, // 5 minutes - data considered fresh
    gcTime: 10 * 60 * 1000, // 10 minutes - cache time (formerly cacheTime)
    refetchOnWindowFocus: false, // Don't refetch on window focus by default
    refetchOnReconnect: true, // Refetch when network reconnects
    retry: (failureCount: number, error: any) => {
      // Don't retry on auth errors
      if (ApiErrorHandler.isAuthError(error)) {
        return false;
      }
      
      // Don't retry on validation errors
      if (ApiErrorHandler.isValidationError(error)) {
        return false;
      }
      
      // Retry up to 3 times for other errors
      return failureCount < 3;
    },
    retryDelay: (attemptIndex: number) => {
      // Exponential backoff: 1s, 2s, 4s
      return Math.min(1000 * 2 ** attemptIndex, 30000);
    },
  },
  mutations: {
    // Global mutation defaults
    retry: (failureCount: number, error: any) => {
      // Don't retry mutations on auth or validation errors
      if (ApiErrorHandler.isAuthError(error) || ApiErrorHandler.isValidationError(error)) {
        return false;
      }
      
      // Retry once for network errors
      if (ApiErrorHandler.isNetworkError(error)) {
        return failureCount < 1;
      }
      
      return false;
    },
  },
};

// Global error handler for React Query
const handleGlobalQueryError = (error: unknown) => {
  // Log error for monitoring
  ErrorHandler.logError(error, 'React Query');
  
  // Handle authentication errors globally
  if (ApiErrorHandler.isAuthError(error)) {
    ErrorHandler.handleAuthError(error as any);
    return;
  }
  
  // Handle rate limit errors globally
  if (ApiErrorHandler.isRateLimitError(error)) {
    ErrorHandler.handleRateLimitError(error as any);
    return;
  }
  
  // Don't show toast for validation errors (handled by forms)
  if (ApiErrorHandler.isValidationError(error)) {
    return;
  }
  
  // Dispatch global error event for toast notifications
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('global:error', {
      detail: { error, context: 'React Query' }
    }));
  }
};

// Create Query Client with comprehensive error handling
export const queryClient = new QueryClient({
  defaultOptions: queryConfig,
  queryCache: new QueryCache({
    onError: handleGlobalQueryError,
  }),
  mutationCache: new MutationCache({
    onError: handleGlobalQueryError,
  }),
});

// Query Keys Factory for consistent key management
export const queryKeys = {
  // Authentication
  auth: {
    user: ['auth', 'user'] as const,
    session: ['auth', 'session'] as const,
  },
  
  // Chat
  chat: {
    all: ['chat'] as const,
    history: (userId: string, page?: number, limit?: number) => 
      ['chat', 'history', userId, { page, limit }] as const,
    conversation: (conversationId: string) => 
      ['chat', 'conversation', conversationId] as const,
  },
  
  // ETL
  etl: {
    all: ['etl'] as const,
    jobs: (userId: string, page?: number, limit?: number) => 
      ['etl', 'jobs', userId, { page, limit }] as const,
    jobStatus: (jobId: string) => 
      ['etl', 'job', jobId, 'status'] as const,
    jobProgress: (jobId: string) => 
      ['etl', 'job', jobId, 'progress'] as const,
  },
  
  // User Management
  user: {
    all: ['user'] as const,
    profile: (userId: string) => 
      ['user', 'profile', userId] as const,
    documents: (userId: string, page?: number, limit?: number, docType?: string) => 
      ['user', 'documents', userId, { page, limit, docType }] as const,
  },
} as const;

// Cache configuration for different data types with optimized strategies
export const cacheConfig = {
  // Authentication data - short cache for security with background refetch
  auth: {
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true, // Refetch auth on focus for security
    refetchInterval: 4 * 60 * 1000, // Background refetch every 4 minutes
  },
  
  // User profile - medium cache with background updates
  userProfile: {
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 15 * 60 * 1000, // 15 minutes
    refetchOnWindowFocus: false,
    refetchInterval: 10 * 60 * 1000, // Background refetch every 10 minutes
  },
  
  // Documents - longer cache as they don't change often
  documents: {
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    refetchOnWindowFocus: false,
    refetchInterval: false, // No background refetch for documents
  },
  
  // Conversation history - medium cache with smart refetching
  conversations: {
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: true, // Refetch to show new conversations
    refetchInterval: false, // No automatic background refetch
  },
  
  // ETL jobs - short cache for real-time updates
  etlJobs: {
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 2 * 60 * 1000, // 2 minutes
    refetchOnWindowFocus: true,
    refetchInterval: (data: any) => {
      // Smart refetching based on job status
      if (data?.jobs?.some((job: any) => 
        job.status === 'running' || job.status === 'pending'
      )) {
        return 15 * 1000; // Refetch every 15 seconds if jobs are running
      }
      return false;
    },
  },
  
  // ETL job status - very short cache for real-time monitoring
  etlJobStatus: {
    staleTime: 5 * 1000, // 5 seconds
    gcTime: 1 * 60 * 1000, // 1 minute
    refetchOnWindowFocus: true,
    refetchInterval: (data: any) => {
      // Auto-refetch if job is still running
      if (data && (data.status === 'running' || data.status === 'pending')) {
        return 3 * 1000; // Refetch every 3 seconds for active jobs
      }
      return false;
    },
  },
  
  // Critical data that needs frequent updates
  critical: {
    staleTime: 0, // Always stale, always refetch
    gcTime: 1 * 60 * 1000, // 1 minute
    refetchOnWindowFocus: true,
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  },
  
  // Static data that rarely changes
  static: {
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
    refetchOnWindowFocus: false,
    refetchInterval: false,
  },
} as const;

// Advanced utility functions for cache management
export const cacheUtils = {
  // Invalidate all queries for a specific user with smart batching
  invalidateUserQueries: async (userId: string) => {
    const invalidations = [
      queryClient.invalidateQueries({ queryKey: queryKeys.user.profile(userId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.user.documents(userId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.chat.history(userId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.etl.jobs(userId) }),
    ];
    
    await Promise.all(invalidations);
  },
  
  // Invalidate authentication queries
  invalidateAuthQueries: async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.auth.user }),
      queryClient.invalidateQueries({ queryKey: queryKeys.auth.session }),
    ]);
  },
  
  // Smart cache invalidation based on data relationships
  invalidateRelatedQueries: async (type: 'user' | 'chat' | 'etl', id: string) => {
    switch (type) {
      case 'user':
        await cacheUtils.invalidateUserQueries(id);
        break;
      case 'chat':
        // Invalidate conversation and related user data
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: queryKeys.chat.conversation(id) }),
          queryClient.invalidateQueries({ queryKey: queryKeys.chat.all }),
        ]);
        break;
      case 'etl':
        // Invalidate ETL job and related user data
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: queryKeys.etl.jobStatus(id) }),
          queryClient.invalidateQueries({ queryKey: queryKeys.etl.all }),
        ]);
        break;
    }
  },
  
  // Clear all cache with confirmation
  clearAllCache: () => {
    queryClient.clear();
  },
  
  // Remove specific query from cache
  removeQuery: (queryKey: readonly unknown[]) => {
    queryClient.removeQueries({ queryKey });
  },
  
  // Advanced prefetching with priority
  prefetchUserData: async (userId: string, priority: 'high' | 'normal' | 'low' = 'normal') => {
    const prefetchPromises: Promise<any>[] = [];
    
    // Always prefetch user profile (high priority)
    prefetchPromises.push(
      queryClient.prefetchQuery({
        queryKey: queryKeys.user.profile(userId),
        queryFn: () => import('@/lib/api').then(api => api.ApiClient.getUserProfile(userId)),
        staleTime: cacheConfig.userProfile.staleTime,
      })
    );
    
    if (priority === 'high' || priority === 'normal') {
      // Prefetch recent conversations
      prefetchPromises.push(
        queryClient.prefetchQuery({
          queryKey: queryKeys.chat.history(userId, 1, 10),
          queryFn: () => import('@/lib/api').then(api => api.ApiClient.getConversationHistory(userId, 1, 10)),
          staleTime: cacheConfig.conversations.staleTime,
        })
      );
      
      // Prefetch recent ETL jobs
      prefetchPromises.push(
        queryClient.prefetchQuery({
          queryKey: queryKeys.etl.jobs(userId, 1, 5),
          queryFn: () => import('@/lib/api').then(api => api.ApiClient.getETLJobs(userId, 1, 5)),
          staleTime: cacheConfig.etlJobs.staleTime,
        })
      );
    }
    
    if (priority === 'high') {
      // Prefetch user documents
      prefetchPromises.push(
        queryClient.prefetchQuery({
          queryKey: queryKeys.user.documents(userId, 1, 20),
          queryFn: () => import('@/lib/api').then(api => api.ApiClient.getUserDocuments(userId, 1, 20)),
          staleTime: cacheConfig.documents.staleTime,
        })
      );
    }
    
    await Promise.allSettled(prefetchPromises);
  },
  
  // Optimistic updates with rollback capability
  optimisticUpdate: <T>(
    queryKey: readonly unknown[], 
    updater: (old: T | undefined) => T,
    rollbackData?: T
  ) => {
    const previousData = queryClient.getQueryData<T>(queryKey);
    
    // Apply optimistic update
    queryClient.setQueryData(queryKey, updater);
    
    // Return rollback function
    return () => {
      queryClient.setQueryData(queryKey, rollbackData ?? previousData);
    };
  },
  
  // Batch optimistic updates
  batchOptimisticUpdates: <T>(
    updates: Array<{
      queryKey: readonly unknown[];
      updater: (old: T | undefined) => T;
      rollbackData?: T;
    }>
  ) => {
    const rollbacks = updates.map(({ queryKey, updater, rollbackData }) => 
      cacheUtils.optimisticUpdate(queryKey, updater, rollbackData)
    );
    
    // Return function to rollback all updates
    return () => {
      rollbacks.forEach(rollback => rollback());
    };
  },
  
  // Update query data with validation
  updateQueryData: <T>(
    queryKey: readonly unknown[], 
    updater: (old: T | undefined) => T,
    validator?: (data: T) => boolean
  ) => {
    const currentData = queryClient.getQueryData<T>(queryKey);
    const newData = updater(currentData);
    
    // Validate new data if validator provided
    if (validator && !validator(newData)) {
      console.warn('Query data update failed validation:', queryKey);
      return false;
    }
    
    queryClient.setQueryData(queryKey, newData);
    return true;
  },
  
  // Get cached data with fallback
  getCachedData: <T>(queryKey: readonly unknown[], fallback?: T): T | undefined => {
    return queryClient.getQueryData<T>(queryKey) ?? fallback;
  },
  
  // Check if query is stale
  isQueryStale: (queryKey: readonly unknown[]): boolean => {
    const query = queryClient.getQueryState(queryKey);
    return !query || query.isStale;
  },
  
  // Get query status
  getQueryStatus: (queryKey: readonly unknown[]) => {
    const query = queryClient.getQueryState(queryKey);
    return {
      exists: !!query,
      isStale: query?.isStale ?? true,
      isFetching: query?.isFetching ?? false,
      isError: query?.isError ?? false,
      lastUpdated: query?.dataUpdatedAt,
    };
  },
  
  // Preload critical data on app start
  preloadCriticalData: async (userId?: string) => {
    const preloadPromises: Promise<any>[] = [];
    
    // Always try to validate session
    preloadPromises.push(
      queryClient.prefetchQuery({
        queryKey: queryKeys.auth.user,
        queryFn: () => import('@/lib/api').then(api => api.ApiClient.validateSession()),
        staleTime: cacheConfig.auth.staleTime,
      }).catch(() => {
        // Ignore auth errors during preload
      })
    );
    
    // If user ID available, preload user data
    if (userId) {
      preloadPromises.push(
        cacheUtils.prefetchUserData(userId, 'high').catch(() => {
          // Ignore errors during preload
        })
      );
    }
    
    await Promise.allSettled(preloadPromises);
  },
  
  // Cache warming for better UX
  warmCache: async (routes: string[], userId?: string) => {
    const warmingPromises: Promise<any>[] = [];
    
    routes.forEach(route => {
      switch (route) {
        case '/chat':
          if (userId) {
            warmingPromises.push(
              queryClient.prefetchQuery({
                queryKey: queryKeys.chat.history(userId, 1, 5),
                queryFn: () => import('@/lib/api').then(api => api.ApiClient.getConversationHistory(userId, 1, 5)),
                staleTime: cacheConfig.conversations.staleTime,
              })
            );
          }
          break;
        case '/profile':
          if (userId) {
            warmingPromises.push(
              queryClient.prefetchQuery({
                queryKey: queryKeys.user.profile(userId),
                queryFn: () => import('@/lib/api').then(api => api.ApiClient.getUserProfile(userId)),
                staleTime: cacheConfig.userProfile.staleTime,
              })
            );
          }
          break;
        case '/documents':
          if (userId) {
            warmingPromises.push(
              queryClient.prefetchQuery({
                queryKey: queryKeys.user.documents(userId, 1, 10),
                queryFn: () => import('@/lib/api').then(api => api.ApiClient.getUserDocuments(userId, 1, 10)),
                staleTime: cacheConfig.documents.staleTime,
              })
            );
          }
          break;
        case '/etl':
          if (userId) {
            warmingPromises.push(
              queryClient.prefetchQuery({
                queryKey: queryKeys.etl.jobs(userId, 1, 10),
                queryFn: () => import('@/lib/api').then(api => api.ApiClient.getETLJobs(userId, 1, 10)),
                staleTime: cacheConfig.etlJobs.staleTime,
              })
            );
          }
          break;
      }
    });
    
    await Promise.allSettled(warmingPromises);
  },
};

// Error boundary for React Query
export const handleQueryError = (error: unknown): ApiError => {
  if (error instanceof Error) {
    // Handle network errors
    if (ApiErrorHandler.isNetworkError(error)) {
      return {
        message: 'Network connection failed. Please check your internet connection.',
        status: 0,
        type: 'network_error',
      } as any;
    }
    
    // Handle API errors
    if ('status' in error && 'message' in error) {
      return error as ApiError;
    }
    
    // Handle unknown errors
    return {
      message: error.message || 'An unexpected error occurred',
      status: 500,
      type: 'server_error',
    } as any;
  }
  
  return {
    message: 'An unexpected error occurred',
    status: 500,
    type: 'server_error',
  } as any;
};

// Performance monitoring and analytics
export const cacheAnalytics = {
  // Track cache hit rates
  getCacheHitRate: () => {
    const cache = queryClient.getQueryCache();
    const queries = cache.getAll();
    
    const stats = queries.reduce((acc, query) => {
      acc.total++;
      if (query.state.data && !query.state.isStale) {
        acc.hits++;
      }
      return acc;
    }, { hits: 0, total: 0 });
    
    return stats.total > 0 ? (stats.hits / stats.total) * 100 : 0;
  },
  
  // Get cache size information
  getCacheStats: () => {
    const cache = queryClient.getQueryCache();
    const queries = cache.getAll();
    
    return {
      totalQueries: queries.length,
      activeQueries: queries.filter(q => q.getObserversCount() > 0).length,
      staleQueries: queries.filter(q => q.state.isStale).length,
      errorQueries: queries.filter(q => q.state.isError).length,
      loadingQueries: queries.filter(q => q.state.isFetching).length,
    };
  },
  
  // Monitor query performance
  getQueryPerformance: (queryKey: readonly unknown[]) => {
    const query = queryClient.getQueryState(queryKey);
    if (!query) return null;
    
    return {
      lastFetchTime: query.dataUpdatedAt,
      errorCount: query.errorUpdateCount,
      fetchCount: query.fetchFailureCount + (query.data ? 1 : 0),
      isStale: query.isStale,
      isFetching: query.isFetching,
    };
  },
  
  // Log cache performance metrics
  logCacheMetrics: () => {
    if (process.env.NODE_ENV === 'development') {
      const hitRate = cacheAnalytics.getCacheHitRate();
      const stats = cacheAnalytics.getCacheStats();
      
      console.group('React Query Cache Metrics');
      console.log('Cache Hit Rate:', `${hitRate.toFixed(2)}%`);
      console.log('Total Queries:', stats.totalQueries);
      console.log('Active Queries:', stats.activeQueries);
      console.log('Stale Queries:', stats.staleQueries);
      console.log('Error Queries:', stats.errorQueries);
      console.log('Loading Queries:', stats.loadingQueries);
      console.groupEnd();
    }
  },
};

// Background cache optimization
export const cacheOptimizer = {
  // Clean up stale queries periodically
  cleanupStaleQueries: () => {
    const cache = queryClient.getQueryCache();
    const queries = cache.getAll();
    
    queries.forEach(query => {
      // Remove queries that haven't been used in 30 minutes
      const lastAccess = query.state.dataUpdatedAt || 0;
      const thirtyMinutesAgo = Date.now() - (30 * 60 * 1000);
      
      if (lastAccess < thirtyMinutesAgo && query.getObserversCount() === 0) {
        cache.remove(query);
      }
    });
  },
  
  // Optimize cache based on usage patterns
  optimizeCache: () => {
    const stats = cacheAnalytics.getCacheStats();
    
    // If we have too many queries, clean up
    if (stats.totalQueries > 100) {
      cacheOptimizer.cleanupStaleQueries();
    }
    
    // Log metrics in development
    if (process.env.NODE_ENV === 'development') {
      cacheAnalytics.logCacheMetrics();
    }
  },
  
  // Start background optimization
  startBackgroundOptimization: () => {
    // Run optimization every 5 minutes
    const interval = setInterval(() => {
      cacheOptimizer.optimizeCache();
    }, 5 * 60 * 1000);
    
    // Return cleanup function
    return () => clearInterval(interval);
  },
};

// React Query DevTools configuration
export const devToolsConfig = {
  initialIsOpen: false,
  position: 'bottom-right' as 'bottom-right',
};

// Initialize background optimization in browser
if (typeof window !== 'undefined') {
  // Start background optimization after a delay
  setTimeout(() => {
    cacheOptimizer.startBackgroundOptimization();
  }, 10000); // Start after 10 seconds
}

export default queryClient;