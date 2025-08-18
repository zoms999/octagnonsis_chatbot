import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React, { Suspense } from 'react';
import { withLazyLoading, LoadingFallbacks, createLazyRoute } from '../lazy-loading';

// Mock the UI components
vi.mock('@/components/ui/loading', () => ({
  Spinner: ({ size }: { size?: string }) => (
    <div data-testid="spinner" role="status" aria-label="Loading">
      Loading {size}...
    </div>
  ),
}));

vi.mock('@/components/ui/skeleton', () => ({
  Skeleton: ({ className }: { className?: string }) => (
    <div data-testid="skeleton" role="status" aria-label="Loading content" className={className}>
      Skeleton
    </div>
  ),
}));

// Mock component for testing
const MockComponent = ({ message }: { message: string }) => (
  <div data-testid="mock-component">{message}</div>
);

// Mock lazy component
const MockLazyComponent = React.lazy(() => 
  Promise.resolve({ default: MockComponent })
);

describe('Lazy Loading Utilities', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('withLazyLoading', () => {
    it('should render lazy component with default loading state', async () => {
      const WrappedComponent = withLazyLoading(MockLazyComponent);
      
      render(<WrappedComponent message="Hello World" />);
      
      // Should show loading initially
      expect(screen.getByTestId('spinner')).toBeInTheDocument();
      
      // Should show component after loading
      await waitFor(() => {
        expect(screen.getByTestId('mock-component')).toBeInTheDocument();
        expect(screen.getByText('Hello World')).toBeInTheDocument();
      });
    });

    it('should render with custom loading component', async () => {
      const CustomLoading = () => <div data-testid="custom-loading">Custom Loading...</div>;
      const WrappedComponent = withLazyLoading(MockLazyComponent, CustomLoading);
      
      render(<WrappedComponent message="Test" />);
      
      // Should show custom loading
      expect(screen.getByTestId('custom-loading')).toBeInTheDocument();
      
      // Should show component after loading
      await waitFor(() => {
        expect(screen.getByTestId('mock-component')).toBeInTheDocument();
      });
    });

    it('should handle loading errors with error boundary', async () => {
      const FailingComponent = React.lazy(() => 
        Promise.reject(new Error('Failed to load'))
      );
      
      const CustomError = ({ error, retry }: { error: Error; retry: () => void }) => (
        <div data-testid="custom-error">
          Error: {error.message}
          <button onClick={retry} data-testid="retry-button">Retry</button>
        </div>
      );
      
      const WrappedComponent = withLazyLoading(FailingComponent, undefined, CustomError);
      
      render(<WrappedComponent />);
      
      // Should show error after failed load
      await waitFor(() => {
        expect(screen.getByTestId('custom-error')).toBeInTheDocument();
        expect(screen.getByText('Error: Failed to load')).toBeInTheDocument();
      });
    });
  });

  describe('LoadingFallbacks', () => {
    it('should render ETL page loading skeleton', () => {
      render(<LoadingFallbacks.ETLPage />);
      
      // Should have skeleton elements
      expect(screen.getAllByTestId('skeleton')).toHaveLength.greaterThan(0);
    });

    it('should render Documents page loading skeleton', () => {
      render(<LoadingFallbacks.DocumentsPage />);
      
      // Should have skeleton elements
      expect(screen.getAllByTestId('skeleton')).toHaveLength.greaterThan(0);
    });

    it('should render Profile page loading skeleton', () => {
      render(<LoadingFallbacks.ProfilePage />);
      
      // Should have skeleton elements
      expect(screen.getAllByTestId('skeleton')).toHaveLength.greaterThan(0);
    });

    it('should render Chat page loading skeleton', () => {
      render(<LoadingFallbacks.ChatPage />);
      
      // Should have skeleton elements
      expect(screen.getAllByTestId('skeleton')).toHaveLength.greaterThan(0);
    });
  });

  describe('createLazyRoute', () => {
    it('should create lazy route with loading component', async () => {
      const LazyRoute = createLazyRoute(
        () => Promise.resolve({ default: MockComponent }),
        () => <div data-testid="route-loading">Route Loading...</div>
      );
      
      render(<LazyRoute message="Route Test" />);
      
      // Should show route loading
      expect(screen.getByTestId('route-loading')).toBeInTheDocument();
      
      // Should show component after loading
      await waitFor(() => {
        expect(screen.getByTestId('mock-component')).toBeInTheDocument();
        expect(screen.getByText('Route Test')).toBeInTheDocument();
      });
    });
  });

  describe('LazyOnVisible', () => {
    beforeEach(() => {
      // Mock IntersectionObserver
      global.IntersectionObserver = vi.fn().mockImplementation((callback) => ({
        observe: vi.fn().mockImplementation(() => {
          // Simulate immediate intersection for testing
          callback([{ isIntersecting: true }]);
        }),
        disconnect: vi.fn(),
      }));
    });

    it('should render children when visible', async () => {
      const { LazyOnVisible } = await import('../lazy-loading');
      
      render(
        <LazyOnVisible fallback={<div data-testid="lazy-fallback">Loading...</div>}>
          <div data-testid="lazy-content">Lazy Content</div>
        </LazyOnVisible>
      );
      
      // Should show content immediately due to mock intersection
      await waitFor(() => {
        expect(screen.getByTestId('lazy-content')).toBeInTheDocument();
      });
    });

    it('should show fallback when not visible', () => {
      // Mock IntersectionObserver to not intersect
      global.IntersectionObserver = vi.fn().mockImplementation(() => ({
        observe: vi.fn(),
        disconnect: vi.fn(),
      }));

      const { LazyOnVisible } = require('../lazy-loading');
      
      render(
        <LazyOnVisible fallback={<div data-testid="lazy-fallback">Loading...</div>}>
          <div data-testid="lazy-content">Lazy Content</div>
        </LazyOnVisible>
      );
      
      // Should show fallback
      expect(screen.getByTestId('lazy-fallback')).toBeInTheDocument();
      expect(screen.queryByTestId('lazy-content')).not.toBeInTheDocument();
    });
  });

  describe('Error Boundary', () => {
    it('should catch and display errors from lazy components', async () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const ThrowingComponent = () => {
        throw new Error('Component error');
      };
      
      const LazyThrowingComponent = React.lazy(() => 
        Promise.resolve({ default: ThrowingComponent })
      );
      
      const WrappedComponent = withLazyLoading(LazyThrowingComponent);
      
      render(<WrappedComponent />);
      
      // Should show error fallback
      await waitFor(() => {
        expect(screen.getByText(/Failed to load component/)).toBeInTheDocument();
        expect(screen.getByText('Try Again')).toBeInTheDocument();
      });
      
      consoleSpy.mockRestore();
    });

    it('should allow retry after error', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      let shouldThrow = true;
      const ConditionalComponent = () => {
        if (shouldThrow) {
          throw new Error('Component error');
        }
        return <div data-testid="success-component">Success!</div>;
      };
      
      const LazyConditionalComponent = React.lazy(() => 
        Promise.resolve({ default: ConditionalComponent })
      );
      
      const WrappedComponent = withLazyLoading(LazyConditionalComponent);
      
      render(<WrappedComponent />);
      
      // Should show error initially
      await waitFor(() => {
        expect(screen.getByText('Try Again')).toBeInTheDocument();
      });
      
      // Fix the component and retry
      shouldThrow = false;
      const retryButton = screen.getByText('Try Again');
      retryButton.click();
      
      // Should show success after retry
      await waitFor(() => {
        expect(screen.getByTestId('success-component')).toBeInTheDocument();
      });
      
      consoleSpy.mockRestore();
    });
  });

  describe('Performance', () => {
    it('should not re-render unnecessarily', async () => {
      let renderCount = 0;
      const CountingComponent = ({ message }: { message: string }) => {
        renderCount++;
        return <div data-testid="counting-component">{message}</div>;
      };
      
      const LazyCountingComponent = React.lazy(() => 
        Promise.resolve({ default: CountingComponent })
      );
      
      const WrappedComponent = withLazyLoading(LazyCountingComponent);
      
      const { rerender } = render(<WrappedComponent message="Test 1" />);
      
      await waitFor(() => {
        expect(screen.getByTestId('counting-component')).toBeInTheDocument();
      });
      
      const initialRenderCount = renderCount;
      
      // Re-render with same props
      rerender(<WrappedComponent message="Test 1" />);
      
      // Should not cause additional renders of the lazy component
      expect(renderCount).toBe(initialRenderCount);
    });
  });
});