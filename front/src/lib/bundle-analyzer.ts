import React from 'react';

/**
 * Bundle analysis utilities for monitoring code splitting effectiveness
 */

interface BundleMetrics {
  totalSize: number;
  gzippedSize: number;
  chunkCount: number;
  loadTime: number;
  cacheHitRate: number;
}

interface ChunkInfo {
  name: string;
  size: number;
  loadTime: number;
  isLazy: boolean;
  dependencies: string[];
}

class BundleAnalyzer {
  private metrics: Map<string, BundleMetrics> = new Map();
  private chunks: Map<string, ChunkInfo> = new Map();
  private loadTimes: Map<string, number[]> = new Map();

  /**
   * Record chunk load time
   */
  recordChunkLoad(chunkName: string, loadTime: number, size?: number) {
    if (!this.loadTimes.has(chunkName)) {
      this.loadTimes.set(chunkName, []);
    }
    
    this.loadTimes.get(chunkName)!.push(loadTime);
    
    // Update chunk info
    if (size) {
      this.chunks.set(chunkName, {
        name: chunkName,
        size,
        loadTime,
        isLazy: true,
        dependencies: [],
      });
    }
  }

  /**
   * Get performance metrics for a chunk
   */
  getChunkMetrics(chunkName: string): BundleMetrics | null {
    const loadTimes = this.loadTimes.get(chunkName);
    if (!loadTimes || loadTimes.length === 0) {
      return null;
    }

    const avgLoadTime = loadTimes.reduce((sum, time) => sum + time, 0) / loadTimes.length;
    const chunk = this.chunks.get(chunkName);

    return {
      totalSize: chunk?.size || 0,
      gzippedSize: Math.round((chunk?.size || 0) * 0.3), // Estimate
      chunkCount: 1,
      loadTime: avgLoadTime,
      cacheHitRate: this.calculateCacheHitRate(chunkName),
    };
  }

  /**
   * Calculate cache hit rate for a chunk
   */
  private calculateCacheHitRate(chunkName: string): number {
    const loadTimes = this.loadTimes.get(chunkName) || [];
    if (loadTimes.length < 2) return 0;

    // Assume cache hit if load time is significantly faster than first load
    const firstLoad = loadTimes[0];
    const subsequentLoads = loadTimes.slice(1);
    const cacheHits = subsequentLoads.filter(time => time < firstLoad * 0.5).length;
    
    return (cacheHits / subsequentLoads.length) * 100;
  }

  /**
   * Get overall bundle performance
   */
  getOverallMetrics(): {
    totalChunks: number;
    averageLoadTime: number;
    totalSize: number;
    lazyChunks: number;
    cacheEfficiency: number;
  } {
    const allLoadTimes: number[] = [];
    let totalSize = 0;
    let lazyChunks = 0;
    let totalCacheHitRate = 0;

    this.chunks.forEach((chunk, name) => {
      const loadTimes = this.loadTimes.get(name) || [];
      allLoadTimes.push(...loadTimes);
      totalSize += chunk.size;
      
      if (chunk.isLazy) {
        lazyChunks++;
      }
      
      totalCacheHitRate += this.calculateCacheHitRate(name);
    });

    const averageLoadTime = allLoadTimes.length > 0 
      ? allLoadTimes.reduce((sum, time) => sum + time, 0) / allLoadTimes.length 
      : 0;

    const averageCacheHitRate = this.chunks.size > 0 
      ? totalCacheHitRate / this.chunks.size 
      : 0;

    return {
      totalChunks: this.chunks.size,
      averageLoadTime,
      totalSize,
      lazyChunks,
      cacheEfficiency: averageCacheHitRate,
    };
  }

  /**
   * Get recommendations for optimization
   */
  getOptimizationRecommendations(): string[] {
    const recommendations: string[] = [];
    const metrics = this.getOverallMetrics();

    if (metrics.averageLoadTime > 1000) {
      recommendations.push('Consider further code splitting - average load time is high');
    }

    if (metrics.lazyChunks / metrics.totalChunks < 0.5) {
      recommendations.push('More components could benefit from lazy loading');
    }

    if (metrics.cacheEfficiency < 70) {
      recommendations.push('Cache hit rate is low - consider preloading strategies');
    }

    // Check for large chunks
    this.chunks.forEach((chunk, name) => {
      if (chunk.size > 100000) { // 100KB
        recommendations.push(`Chunk "${name}" is large (${Math.round(chunk.size / 1024)}KB) - consider splitting further`);
      }
    });

    // Check for slow chunks
    this.loadTimes.forEach((times, name) => {
      const avgTime = times.reduce((sum, time) => sum + time, 0) / times.length;
      if (avgTime > 2000) { // 2 seconds
        recommendations.push(`Chunk "${name}" loads slowly (${Math.round(avgTime)}ms) - investigate optimization`);
      }
    });

    return recommendations;
  }

  /**
   * Export metrics for analysis
   */
  exportMetrics() {
    return {
      chunks: Array.from(this.chunks.entries()).map(([name, info]) => ({
        name,
        ...info,
        metrics: this.getChunkMetrics(name),
      })),
      overall: this.getOverallMetrics(),
      recommendations: this.getOptimizationRecommendations(),
    };
  }

  /**
   * Clear all metrics
   */
  clear() {
    this.metrics.clear();
    this.chunks.clear();
    this.loadTimes.clear();
  }
}

// Global bundle analyzer instance
export const bundleAnalyzer = new BundleAnalyzer();

/**
 * Hook for measuring component load times
 */
export function useBundleMetrics(componentName: string) {
  const startTime = React.useRef<number>(0);

  React.useEffect(() => {
    startTime.current = performance.now();
    
    return () => {
      const loadTime = performance.now() - startTime.current;
      bundleAnalyzer.recordChunkLoad(componentName, loadTime);
    };
  }, [componentName]);
}

/**
 * Higher-order component for measuring load times
 */
export function withBundleMetrics<T extends object>(
  Component: React.ComponentType<T>,
  componentName: string
): React.ComponentType<T> {
  const WrappedComponent = (props: T) => {
    useBundleMetrics(componentName);
    return React.createElement(Component, props);
  };

  WrappedComponent.displayName = `withBundleMetrics(${componentName})`;
  return WrappedComponent;
}

/**
 * Performance observer for monitoring resource loading
 */
export function initializeBundleMonitoring() {
  if (typeof window === 'undefined') return;

  // Monitor resource loading
  if ('PerformanceObserver' in window) {
    const observer = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        if (entry.entryType === 'resource' && entry.name.includes('chunk')) {
          const chunkName = extractChunkName(entry.name);
          if (chunkName) {
            bundleAnalyzer.recordChunkLoad(
              chunkName,
              entry.duration,
              (entry as any).transferSize
            );
          }
        }
      });
    });

    observer.observe({ entryTypes: ['resource'] });
  }

  // Log metrics periodically in development
  if (process.env.NODE_ENV === 'development') {
    setInterval(() => {
      const metrics = bundleAnalyzer.getOverallMetrics();
      if (metrics.totalChunks > 0) {
        console.group('📦 Bundle Performance Metrics');
        console.log('Total Chunks:', metrics.totalChunks);
        console.log('Lazy Chunks:', metrics.lazyChunks);
        console.log('Average Load Time:', `${Math.round(metrics.averageLoadTime)}ms`);
        console.log('Total Size:', `${Math.round(metrics.totalSize / 1024)}KB`);
        console.log('Cache Efficiency:', `${Math.round(metrics.cacheEfficiency)}%`);
        
        const recommendations = bundleAnalyzer.getOptimizationRecommendations();
        if (recommendations.length > 0) {
          console.log('💡 Recommendations:', recommendations);
        }
        
        console.groupEnd();
      }
    }, 30000); // Every 30 seconds
  }
}

/**
 * Extract chunk name from resource URL
 */
function extractChunkName(url: string): string | null {
  const match = url.match(/\/([^\/]+)\.chunk\./);
  return match ? match[1] : null;
}

/**
 * Development helper to log bundle analysis
 */
export function logBundleAnalysis() {
  if (process.env.NODE_ENV === 'development') {
    console.log('📊 Bundle Analysis:', bundleAnalyzer.exportMetrics());
  }
}

// Initialize monitoring when module loads
if (typeof window !== 'undefined') {
  initializeBundleMonitoring();
}