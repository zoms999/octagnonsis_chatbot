import { useEffect, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { cacheAnalytics, cacheOptimizer } from '@/lib/react-query';

interface PerformanceMetrics {
  cacheHitRate: number;
  queryCount: number;
  activeQueries: number;
  staleQueries: number;
  errorQueries: number;
  loadingQueries: number;
  memoryUsage?: number;
}

interface QueryPerformanceData {
  queryKey: string;
  fetchCount: number;
  errorCount: number;
  averageResponseTime: number;
  lastFetchTime: number;
  cacheHits: number;
}

/**
 * Hook for monitoring React Query performance and cache efficiency
 */
export function usePerformanceMonitoring(enabled: boolean = process.env.NODE_ENV === 'development') {
  const queryClient = useQueryClient();
  const metricsRef = useRef<PerformanceMetrics[]>([]);
  const queryPerformanceRef = useRef<Map<string, QueryPerformanceData>>(new Map());

  // Collect performance metrics
  const collectMetrics = useCallback((): PerformanceMetrics => {
    const stats = cacheAnalytics.getCacheStats();
    const hitRate = cacheAnalytics.getCacheHitRate();
    
    const metrics: PerformanceMetrics = {
      cacheHitRate: hitRate,
      queryCount: stats.totalQueries,
      activeQueries: stats.activeQueries,
      staleQueries: stats.staleQueries,
      errorQueries: stats.errorQueries,
      loadingQueries: stats.loadingQueries,
    };

    // Add memory usage if available
    if ('memory' in performance && (performance as any).memory) {
      metrics.memoryUsage = (performance as any).memory.usedJSHeapSize;
    }

    return metrics;
  }, []);

  // Track query performance over time
  const trackQueryPerformance = useCallback((queryKey: readonly unknown[], responseTime: number, isError: boolean = false) => {
    if (!enabled) return;

    const keyString = JSON.stringify(queryKey);
    const existing = queryPerformanceRef.current.get(keyString);

    if (existing) {
      const newFetchCount = existing.fetchCount + 1;
      const newErrorCount = existing.errorCount + (isError ? 1 : 0);
      const newAverageResponseTime = (existing.averageResponseTime * existing.fetchCount + responseTime) / newFetchCount;

      queryPerformanceRef.current.set(keyString, {
        ...existing,
        fetchCount: newFetchCount,
        errorCount: newErrorCount,
        averageResponseTime: newAverageResponseTime,
        lastFetchTime: Date.now(),
      });
    } else {
      queryPerformanceRef.current.set(keyString, {
        queryKey: keyString,
        fetchCount: 1,
        errorCount: isError ? 1 : 0,
        averageResponseTime: responseTime,
        lastFetchTime: Date.now(),
        cacheHits: 0,
      });
    }
  }, [enabled]);

  // Get performance report
  const getPerformanceReport = useCallback(() => {
    const currentMetrics = collectMetrics();
    const recentMetrics = metricsRef.current.slice(-10); // Last 10 measurements
    
    const averageHitRate = recentMetrics.length > 0 
      ? recentMetrics.reduce((sum, m) => sum + m.cacheHitRate, 0) / recentMetrics.length
      : currentMetrics.cacheHitRate;

    const slowQueries = Array.from(queryPerformanceRef.current.values())
      .filter(q => q.averageResponseTime > 1000) // Queries taking more than 1 second
      .sort((a, b) => b.averageResponseTime - a.averageResponseTime)
      .slice(0, 5); // Top 5 slowest queries

    const errorProneQueries = Array.from(queryPerformanceRef.current.values())
      .filter(q => q.errorCount > 0)
      .sort((a, b) => (b.errorCount / b.fetchCount) - (a.errorCount / a.fetchCount))
      .slice(0, 5); // Top 5 error-prone queries

    return {
      current: currentMetrics,
      trends: {
        averageHitRate,
        hitRateTrend: recentMetrics.length > 1 
          ? currentMetrics.cacheHitRate - recentMetrics[recentMetrics.length - 2].cacheHitRate
          : 0,
      },
      slowQueries,
      errorProneQueries,
      recommendations: generateRecommendations(currentMetrics, slowQueries, errorProneQueries),
    };
  }, [collectMetrics]);

  // Generate performance recommendations
  const generateRecommendations = (
    metrics: PerformanceMetrics,
    slowQueries: QueryPerformanceData[],
    errorProneQueries: QueryPerformanceData[]
  ): string[] => {
    const recommendations: string[] = [];

    if (metrics.cacheHitRate < 70) {
      recommendations.push('Cache hit rate is low. Consider increasing stale times for stable data.');
    }

    if (metrics.staleQueries > metrics.queryCount * 0.5) {
      recommendations.push('Many queries are stale. Consider background refetching for critical data.');
    }

    if (slowQueries.length > 0) {
      recommendations.push(`${slowQueries.length} queries are slow. Consider optimizing or adding loading states.`);
    }

    if (errorProneQueries.length > 0) {
      recommendations.push(`${errorProneQueries.length} queries have high error rates. Review error handling.`);
    }

    if (metrics.activeQueries > 20) {
      recommendations.push('Many active queries detected. Consider query cleanup or lazy loading.');
    }

    return recommendations;
  };

  // Monitor query cache events
  useEffect(() => {
    if (!enabled) return;

    const cache = queryClient.getQueryCache();
    
    const unsubscribe = cache.subscribe((event) => {
      if (event?.type === 'updated' && event.query) {
        const query = event.query;
        const keyString = JSON.stringify(query.queryKey);
        
        // Track cache hits
        if (query.state.data && !query.state.isFetching) {
          const existing = queryPerformanceRef.current.get(keyString);
          if (existing) {
            queryPerformanceRef.current.set(keyString, {
              ...existing,
              cacheHits: existing.cacheHits + 1,
            });
          }
        }
      }
    });

    return unsubscribe;
  }, [enabled, queryClient]);

  // Collect metrics periodically
  useEffect(() => {
    if (!enabled) return;

    const collectAndStore = () => {
      const metrics = collectMetrics();
      metricsRef.current.push(metrics);
      
      // Keep only last 50 measurements
      if (metricsRef.current.length > 50) {
        metricsRef.current = metricsRef.current.slice(-50);
      }
    };

    // Initial collection
    collectAndStore();

    // Collect every 30 seconds
    const interval = setInterval(collectAndStore, 30000);

    return () => clearInterval(interval);
  }, [enabled, collectMetrics]);

  // Log performance warnings
  useEffect(() => {
    if (!enabled) return;

    const checkPerformance = () => {
      const report = getPerformanceReport();
      
      if (report.current.cacheHitRate < 50) {
        console.warn('React Query: Low cache hit rate detected:', report.current.cacheHitRate.toFixed(2) + '%');
      }
      
      if (report.slowQueries.length > 0) {
        console.warn('React Query: Slow queries detected:', report.slowQueries);
      }
      
      if (report.errorProneQueries.length > 0) {
        console.warn('React Query: Error-prone queries detected:', report.errorProneQueries);
      }
    };

    // Check every 2 minutes
    const interval = setInterval(checkPerformance, 2 * 60 * 1000);

    return () => clearInterval(interval);
  }, [enabled, getPerformanceReport]);

  return {
    collectMetrics,
    trackQueryPerformance,
    getPerformanceReport,
    isEnabled: enabled,
  };
}

/**
 * Hook for automatic performance optimization
 */
export function useAutoOptimization(enabled: boolean = true) {
  const { getPerformanceReport } = usePerformanceMonitoring();

  useEffect(() => {
    if (!enabled) return;

    const optimize = () => {
      const report = getPerformanceReport();
      
      // Auto-cleanup if cache hit rate is very low
      if (report.current.cacheHitRate < 30) {
        cacheOptimizer.cleanupStaleQueries();
      }
      
      // Auto-optimize if too many queries
      if (report.current.queryCount > 100) {
        cacheOptimizer.optimizeCache();
      }
    };

    // Run optimization every 5 minutes
    const interval = setInterval(optimize, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [enabled, getPerformanceReport]);
}

/**
 * Hook for performance debugging in development
 */
export function usePerformanceDebugger() {
  const { getPerformanceReport, isEnabled } = usePerformanceMonitoring();

  const logPerformanceReport = useCallback(() => {
    if (!isEnabled) return;

    const report = getPerformanceReport();
    
    console.group('🚀 React Query Performance Report');
    console.log('📊 Current Metrics:', report.current);
    console.log('📈 Trends:', report.trends);
    
    if (report.slowQueries.length > 0) {
      console.log('🐌 Slow Queries:', report.slowQueries);
    }
    
    if (report.errorProneQueries.length > 0) {
      console.log('❌ Error-Prone Queries:', report.errorProneQueries);
    }
    
    if (report.recommendations.length > 0) {
      console.log('💡 Recommendations:', report.recommendations);
    }
    
    console.groupEnd();
  }, [getPerformanceReport, isEnabled]);

  // Expose to window for manual debugging
  useEffect(() => {
    if (typeof window !== 'undefined' && isEnabled) {
      (window as any).logReactQueryPerformance = logPerformanceReport;
    }
  }, [logPerformanceReport, isEnabled]);

  return {
    logPerformanceReport,
  };
}