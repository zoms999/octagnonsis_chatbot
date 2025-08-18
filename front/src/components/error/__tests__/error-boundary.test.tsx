import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import ErrorBoundary, { withErrorBoundary, AsyncErrorBoundary } from '../error-boundary';

// Mock console.error to avoid noise in tests
const originalConsoleError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalConsoleError;
});

// Test component that throws an error
const ThrowError = ({ shouldThrow = false }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

// Test component for async errors
const AsyncThrowError = ({ shouldThrow = false }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    Promise.reject(new Error('Async test error'));
  }
  return <div>No async error</div>;
};

describe('ErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('renders error UI when child component throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/An unexpected error occurred/)).toBeInTheDocument();
  });

  it('shows technical details in development mode', () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Technical Details')).toBeInTheDocument();

    process.env.NODE_ENV = originalEnv;
  });

  it('calls onError callback when error occurs', () => {
    const onError = vi.fn();

    render(
      <ErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      })
    );
  });

  it('renders custom fallback when provided', () => {
    const customFallback = (error: Error) => (
      <div>Custom error: {error.message}</div>
    );

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error: Test error')).toBeInTheDocument();
  });

  it('resets error boundary when Try Again is clicked', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Try Again'));

    rerender(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('No error')).toBeInTheDocument();
  });

  it('reloads page when Reload Page is clicked', () => {
    // Mock window.location.reload
    const mockReload = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { reload: mockReload },
      writable: true,
    });

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    fireEvent.click(screen.getByText('Reload Page'));

    expect(mockReload).toHaveBeenCalled();
  });

  it('resets on props change when resetOnPropsChange is true', () => {
    let shouldThrow = true;
    const resetKey = 'test-key';

    const { rerender } = render(
      <ErrorBoundary resetOnPropsChange={true} resetKeys={[resetKey]}>
        <ThrowError shouldThrow={shouldThrow} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Change reset key to trigger reset
    shouldThrow = false;
    rerender(
      <ErrorBoundary resetOnPropsChange={true} resetKeys={['new-key']}>
        <ThrowError shouldThrow={shouldThrow} />
      </ErrorBoundary>
    );

    expect(screen.getByText('No error')).toBeInTheDocument();
  });
});

describe('withErrorBoundary HOC', () => {
  it('wraps component with error boundary', () => {
    const TestComponent = () => <div>Test component</div>;
    const WrappedComponent = withErrorBoundary(TestComponent);

    render(<WrappedComponent />);

    expect(screen.getByText('Test component')).toBeInTheDocument();
  });

  it('catches errors in wrapped component', () => {
    const WrappedComponent = withErrorBoundary(ThrowError);

    render(<WrappedComponent shouldThrow={true} />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('passes error boundary props to wrapper', () => {
    const onError = vi.fn();
    const WrappedComponent = withErrorBoundary(ThrowError, { onError });

    render(<WrappedComponent shouldThrow={true} />);

    expect(onError).toHaveBeenCalled();
  });
});

describe('AsyncErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <AsyncErrorBoundary>
        <div>Test content</div>
      </AsyncErrorBoundary>
    );

    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('handles unhandled promise rejections', async () => {
    // Mock window.addEventListener
    const addEventListener = vi.fn();
    const removeEventListener = vi.fn();
    
    Object.defineProperty(window, 'addEventListener', {
      value: addEventListener,
      writable: true,
    });
    
    Object.defineProperty(window, 'removeEventListener', {
      value: removeEventListener,
      writable: true,
    });

    render(
      <AsyncErrorBoundary>
        <AsyncThrowError />
      </AsyncErrorBoundary>
    );

    expect(addEventListener).toHaveBeenCalledWith(
      'unhandledrejection',
      expect.any(Function)
    );

    // Cleanup should remove event listener
    screen.getByText('No async error').remove();
    
    expect(removeEventListener).toHaveBeenCalledWith(
      'unhandledrejection',
      expect.any(Function)
    );
  });
});

describe('Error Boundary Integration', () => {
  it('works with multiple nested error boundaries', () => {
    render(
      <ErrorBoundary>
        <div>Outer boundary</div>
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      </ErrorBoundary>
    );

    // Inner boundary should catch the error
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    // Outer boundary content should still be visible
    expect(screen.getByText('Outer boundary')).toBeInTheDocument();
  });

  it('handles errors during error boundary rendering', () => {
    const BadFallback = () => {
      throw new Error('Fallback error');
    };

    // This should be caught by a parent error boundary or default error handling
    expect(() => {
      render(
        <ErrorBoundary fallback={BadFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
    }).toThrow('Fallback error');
  });
});