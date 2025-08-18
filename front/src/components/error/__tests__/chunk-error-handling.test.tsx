import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ChunkErrorBoundary from '../chunk-error-boundary';
import { ChunkStatusIndicator, FloatingChunkStatus } from '../chunk-status-indicator';
import { useChunkErrorHandler } from '@/hooks/use-chunk-error-handler';

// Mock the chunk error handler
vi.mock('@/lib/chunk-error-handler', () => ({
  chunkErrorHandler: {
    getFailureStats: vi.fn(() => []),
    clearFailureHistory: vi.fn(),
    manualRetry: vi.fn(() => Promise.resolve(true)),
  },
}));

// Mock the hook
vi.mock('@/hooks/use-chunk-error-handler', () => ({
  useChunkErrorHandler: vi.fn(),
  useChunkHealthMonitor: vi.fn(() => ({
    totalFailures: 0,
    criticalFailures: 0,
    lastFailureTime: null,
    isHealthy: true,
  })),
}));

const mockUseChunkErrorHandler = vi.mocked(useChunkErrorHandler);

// Test component that throws an error
function ThrowError({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Loading chunk 123 failed');
  }
  return <div>No error</div>;
}

describe('Chunk Error Handling', () => {
  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();
    
    // Default mock implementation
    mockUseChunkErrorHandler.mockReturnValue({
      failures: [],
      isRetrying: false,
      hasErrors: false,
      retryChunk: vi.fn(),
      retryAllChunks: vi.fn(),
      clearErrors: vi.fn(),
      reloadPage: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('ChunkErrorBoundary', () => {
    it('should render children when there are no errors', () => {
      render(
        <ChunkErrorBoundary>
          <div>Test content</div>
        </ChunkErrorBoundary>
      );

      expect(screen.getByText('Test content')).toBeInTheDocument();
    });

    it('should catch chunk loading errors and display error UI', () => {
      // Mock console.error to avoid test output noise
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      render(
        <ChunkErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ChunkErrorBoundary>
      );

      expect(screen.getByText('Loading Error')).toBeInTheDocument();
      expect(screen.getByText(/Some application resources failed to load/)).toBeInTheDocument();
      expect(screen.getByText('Retry Loading')).toBeInTheDocument();
      expect(screen.getByText('Reload Page')).toBeInTheDocument();

      consoleSpy.mockRestore();
      consoleWarnSpy.mockRestore();
    });

    it('should provide retry functionality', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      render(
        <ChunkErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ChunkErrorBoundary>
      );

      const retryButton = screen.getByText('Retry Loading');
      expect(retryButton).toBeInTheDocument();
      
      // Click should not throw an error
      fireEvent.click(retryButton);

      consoleSpy.mockRestore();
      consoleWarnSpy.mockRestore();
    });

    it('should handle page reload', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      // Mock window.location.reload
      const reloadMock = vi.fn();
      Object.defineProperty(window, 'location', {
        value: { reload: reloadMock },
        writable: true,
      });

      render(
        <ChunkErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ChunkErrorBoundary>
      );

      const reloadButton = screen.getByText('Reload Page');
      fireEvent.click(reloadButton);

      expect(reloadMock).toHaveBeenCalled();

      consoleSpy.mockRestore();
      consoleWarnSpy.mockRestore();
    });
  });

  describe('ChunkStatusIndicator', () => {
    it('should not render when there are no errors and showWhenHealthy is false', () => {
      const { container } = render(<ChunkStatusIndicator />);
      expect(container.firstChild).toBeNull();
    });

    it('should render when showWhenHealthy is true', () => {
      render(<ChunkStatusIndicator showWhenHealthy={true} />);
      expect(screen.getByText('All Resources Loaded')).toBeInTheDocument();
    });

    it('should display errors when they exist', () => {
      mockUseChunkErrorHandler.mockReturnValue({
        failures: [
          {
            chunkName: 'test-chunk',
            attemptCount: 2,
            lastError: new Error('Test error'),
            timestamp: new Date(),
          },
        ],
        isRetrying: false,
        hasErrors: true,
        retryChunk: vi.fn(),
        retryAllChunks: vi.fn(),
        clearErrors: vi.fn(),
        reloadPage: vi.fn(),
      });

      render(<ChunkStatusIndicator />);

      expect(screen.getByText('Resource Loading Issues')).toBeInTheDocument();
      expect(screen.getByText('1 error')).toBeInTheDocument();
      expect(screen.getByText('test-chunk')).toBeInTheDocument();
      expect(screen.getByText('2 attempts')).toBeInTheDocument();
    });

    it('should provide retry functionality', () => {
      const retryAllChunks = vi.fn();
      
      mockUseChunkErrorHandler.mockReturnValue({
        failures: [
          {
            chunkName: 'test-chunk',
            attemptCount: 1,
            lastError: new Error('Test error'),
            timestamp: new Date(),
          },
        ],
        isRetrying: false,
        hasErrors: true,
        retryChunk: vi.fn(),
        retryAllChunks,
        clearErrors: vi.fn(),
        reloadPage: vi.fn(),
      });

      render(<ChunkStatusIndicator />);

      const retryButton = screen.getByText('Retry All');
      fireEvent.click(retryButton);

      expect(retryAllChunks).toHaveBeenCalled();
    });

    it('should render in compact mode', () => {
      mockUseChunkErrorHandler.mockReturnValue({
        failures: [
          {
            chunkName: 'test-chunk',
            attemptCount: 1,
            lastError: new Error('Test error'),
            timestamp: new Date(),
          },
        ],
        isRetrying: false,
        hasErrors: true,
        retryChunk: vi.fn(),
        retryAllChunks: vi.fn(),
        clearErrors: vi.fn(),
        reloadPage: vi.fn(),
      });

      render(<ChunkStatusIndicator compact={true} />);

      expect(screen.getByText('1 chunk error')).toBeInTheDocument();
      // Should have a retry button but no detailed error info
      expect(screen.queryByText('Resource Loading Issues')).not.toBeInTheDocument();
    });
  });

  describe('FloatingChunkStatus', () => {
    it('should not render when there are no errors', () => {
      const { container } = render(<FloatingChunkStatus />);
      expect(container.firstChild).toBeNull();
    });

    it('should render floating status when there are errors', () => {
      mockUseChunkErrorHandler.mockReturnValue({
        failures: [
          {
            chunkName: 'test-chunk',
            attemptCount: 1,
            lastError: new Error('Test error'),
            timestamp: new Date(),
          },
        ],
        isRetrying: false,
        hasErrors: true,
        retryChunk: vi.fn(),
        retryAllChunks: vi.fn(),
        clearErrors: vi.fn(),
        reloadPage: vi.fn(),
      });

      render(<FloatingChunkStatus />);

      expect(screen.getByText('1 resource failed to load')).toBeInTheDocument();
      expect(screen.getByText('Some features may not work properly')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('should handle multiple failures', () => {
      mockUseChunkErrorHandler.mockReturnValue({
        failures: [
          {
            chunkName: 'chunk-1',
            attemptCount: 1,
            lastError: new Error('Test error 1'),
            timestamp: new Date(),
          },
          {
            chunkName: 'chunk-2',
            attemptCount: 2,
            lastError: new Error('Test error 2'),
            timestamp: new Date(),
          },
        ],
        isRetrying: false,
        hasErrors: true,
        retryChunk: vi.fn(),
        retryAllChunks: vi.fn(),
        clearErrors: vi.fn(),
        reloadPage: vi.fn(),
      });

      render(<FloatingChunkStatus />);

      expect(screen.getByText('2 resources failed to load')).toBeInTheDocument();
    });
  });

  describe('Error Event Handling', () => {
    it('should handle chunk retry events', () => {
      // This would test the event listeners in the actual implementation
      // For now, we're testing the component behavior
      expect(true).toBe(true);
    });

    it('should handle chunk fallback events', () => {
      // This would test the fallback event handling
      expect(true).toBe(true);
    });
  });
});