import { describe, it, expect, beforeEach } from 'vitest';
import { bundleAnalyzer } from '../bundle-analyzer';

describe('Bundle Analyzer', () => {
  beforeEach(() => {
    bundleAnalyzer.clear();
  });

  it('should record chunk load times', () => {
    bundleAnalyzer.recordChunkLoad('test-chunk', 100, 1024);
    
    const metrics = bundleAnalyzer.getChunkMetrics('test-chunk');
    expect(metrics).toBeDefined();
    expect(metrics?.loadTime).toBe(100);
    expect(metrics?.totalSize).toBe(1024);
  });

  it('should calculate average load times', () => {
    bundleAnalyzer.recordChunkLoad('test-chunk', 100);
    bundleAnalyzer.recordChunkLoad('test-chunk', 200);
    bundleAnalyzer.recordChunkLoad('test-chunk', 300);
    
    const metrics = bundleAnalyzer.getChunkMetrics('test-chunk');
    expect(metrics?.loadTime).toBe(200); // Average of 100, 200, 300
  });

  it('should provide overall metrics', () => {
    bundleAnalyzer.recordChunkLoad('chunk1', 100, 1024);
    bundleAnalyzer.recordChunkLoad('chunk2', 200, 2048);
    
    const overall = bundleAnalyzer.getOverallMetrics();
    expect(overall.totalChunks).toBe(2);
    expect(overall.totalSize).toBe(3072); // 1024 + 2048
    expect(overall.averageLoadTime).toBe(150); // (100 + 200) / 2
  });

  it('should generate optimization recommendations', () => {
    // Add a large chunk
    bundleAnalyzer.recordChunkLoad('large-chunk', 100, 200000); // 200KB
    
    const recommendations = bundleAnalyzer.getOptimizationRecommendations();
    expect(recommendations.length).toBeGreaterThan(0);
    expect(recommendations.some(r => r.includes('large-chunk'))).toBe(true);
  });

  it('should export metrics for analysis', () => {
    bundleAnalyzer.recordChunkLoad('test-chunk', 100, 1024);
    
    const exported = bundleAnalyzer.exportMetrics();
    expect(exported).toHaveProperty('chunks');
    expect(exported).toHaveProperty('overall');
    expect(exported).toHaveProperty('recommendations');
    expect(exported.chunks).toHaveLength(1);
  });
});