import React, { Suspense, ComponentType, LazyExoticComponent } from 'react';
import { Spinner } from '@/components/ui/loading';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * Higher-order component for lazy loading with custom loading states
 */
export function withLazyLoading<T extends object>(
  LazyComponent: LazyExoticComponent<ComponentType<T>>,
  LoadingComponent?: ComponentType,
  errorFallback?: ComponentType<{ error: Error; retry: () => void }>
) {
  const WrappedComponent = (props: T) => {
    const ErrorFallback = errorFallback || DefaultErrorFallback;
    const LoadingFallback = LoadingComponent || DefaultLoadingFallback;

    return (
      <ErrorBoundary fallback={ErrorFallback}>
        <Suspense fallback={<LoadingFallback />}>
          <LazyComponent {...props} />
        </Suspense>
      </ErrorBoundary>
    );
  };

  WrappedComponent.displayName = `withLazyLoading(${LazyComponent.displayName || 'Component'})`;
  
  return WrappedComponent;
}

/**
 * Error boundary for lazy-loaded components
 */
class ErrorBoundary extends React.Component<
  { 
    children: React.ReactNode; 
    fallback: ComponentType<{ error: Error; retry: () => void }> 
  },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Lazy loading error:', error, errorInfo);
  }

  retry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      const FallbackComponent = this.props.fallback;
      return <FallbackComponent error={this.state.error} retry={this.retry} />;
    }

    return this.props.children;
  }
}

/**
 * Default loading fallback component
 */
function DefaultLoadingFallback() {
  return (
    <div className="flex items-center justify-center p-8">
      <Spinner size="lg" />
    </div>
  );
}

/**
 * Default error fallback component
 */
function DefaultErrorFallback({ error, retry }: { error: Error; retry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="text-red-500 text-4xl mb-4">⚠️</div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        Failed to load component
      </h3>
      <p className="text-gray-600 mb-4">
        {error.message || 'An unexpected error occurred while loading this component.'}
      </p>
      <button
        onClick={retry}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}

/**
 * Specialized loading components for different page types
 */
export const LoadingFallbacks = {
  // ETL page loading skeleton
  ETLPage: () => (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
      
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    </div>
  ),

  // Documents page loading skeleton
  DocumentsPage: () => (
    <div className="container mx-auto px-4 py-6 max-w-6xl space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-4 w-64" />
      </div>
      
      <Skeleton className="h-12 w-full" />
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
    </div>
  ),

  // Profile page loading skeleton
  ProfilePage: () => (
    <div className="container mx-auto px-4 py-6 max-w-4xl space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-24" />
        <Skeleton className="h-4 w-48" />
      </div>
      
      <div className="bg-white rounded-lg border p-6 space-y-4">
        <div className="flex items-center space-x-4">
          <Skeleton className="h-16 w-16 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-24" />
          </div>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="text-center space-y-2">
              <Skeleton className="h-8 w-16 mx-auto" />
              <Skeleton className="h-4 w-20 mx-auto" />
            </div>
          ))}
        </div>
      </div>
    </div>
  ),

  // Chat page loading skeleton
  ChatPage: () => (
    <div className="h-full flex flex-col">
      <div className="mb-6 space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-64" />
      </div>

      <div className="flex-1 bg-card rounded-lg border p-4">
        <div className="h-full flex flex-col">
          <div className="flex-1 space-y-4 mb-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className={`flex ${i % 2 === 0 ? 'justify-end' : 'justify-start'}`}>
                <Skeleton className={`h-12 ${i % 2 === 0 ? 'w-64' : 'w-80'} rounded-lg`} />
              </div>
            ))}
          </div>
          <Skeleton className="h-12 w-full" />
        </div>
      </div>
    </div>
  ),

  // Generic component loading
  Component: () => (
    <div className="flex items-center justify-center p-4">
      <Spinner />
    </div>
  ),
};

/**
 * Preload a lazy component
 */
export function preloadComponent<T>(
  lazyComponent: LazyExoticComponent<ComponentType<T>>
): Promise<{ default: ComponentType<T> }> {
  return lazyComponent as any;
}

/**
 * Create a lazy component with route-based code splitting
 */
export function createLazyRoute<T extends object>(
  importFn: () => Promise<{ default: ComponentType<T> }>,
  loadingComponent?: ComponentType,
  errorFallback?: ComponentType<{ error: Error; retry: () => void }>
) {
  const LazyComponent = React.lazy(importFn);
  return withLazyLoading(LazyComponent, loadingComponent, errorFallback);
}

/**
 * Hook for preloading components on hover or focus
 */
export function usePreloadOnHover<T>(
  lazyComponent: LazyExoticComponent<ComponentType<T>>
) {
  const preload = React.useCallback(() => {
    preloadComponent(lazyComponent);
  }, [lazyComponent]);

  return {
    onMouseEnter: preload,
    onFocus: preload,
  };
}

/**
 * Component for intersection-based lazy loading
 */
export function LazyOnVisible({ 
  children, 
  fallback = <LoadingFallbacks.Component />,
  rootMargin = '50px' 
}: {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  rootMargin?: string;
}) {
  const [isVisible, setIsVisible] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [rootMargin]);

  return (
    <div ref={ref}>
      {isVisible ? children : fallback}
    </div>
  );
}