import { useEffect, useCallback, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { preloadComponents } from '@/components/lazy';

interface PreloadingConfig {
  enabled: boolean;
  preloadOnHover: boolean;
  preloadOnIdle: boolean;
  preloadDelay: number;
  maxConcurrentPreloads: number;
}

const defaultConfig: PreloadingConfig = {
  enabled: true,
  preloadOnHover: true,
  preloadOnIdle: true,
  preloadDelay: 2000, // 2 seconds
  maxConcurrentPreloads: 2,
};

/**
 * Hook for intelligent component preloading based on user behavior
 */
export function useComponentPreloading(config: Partial<PreloadingConfig> = {}) {
  const finalConfig = { ...defaultConfig, ...config };
  const pathname = usePathname();
  const router = useRouter();
  const preloadedRoutes = useRef(new Set<string>());
  const preloadQueue = useRef<Array<() => Promise<any>>>([]);
  const activePreloads = useRef(0);

  // Route-based preloading strategy
  const getPreloadTargets = useCallback((currentPath: string): string[] => {
    const routeMap: Record<string, string[]> = {
      '/chat': ['documents', 'profile'], // From chat, users often go to documents or profile
      '/profile': ['documents', 'etl'], // From profile, users check documents or ETL
      '/documents': ['etl', 'chat'], // From documents, users check ETL or go back to chat
      '/etl': ['documents', 'profile'], // From ETL, users check documents or profile
      '/history': ['chat', 'profile'], // From history, users go back to chat or profile
    };

    return routeMap[currentPath] || [];
  }, []);

  // Execute preload with concurrency control
  const executePreload = useCallback(async (preloadFn: () => Promise<any>) => {
    if (activePreloads.current >= finalConfig.maxConcurrentPreloads) {
      preloadQueue.current.push(preloadFn);
      return;
    }

    activePreloads.current++;
    
    try {
      await preloadFn();
    } catch (error) {
      console.warn('Component preload failed:', error);
    } finally {
      activePreloads.current--;
      
      // Process next item in queue
      const nextPreload = preloadQueue.current.shift();
      if (nextPreload) {
        executePreload(nextPreload);
      }
    }
  }, [finalConfig.maxConcurrentPreloads]);

  // Preload components for a specific route
  const preloadRoute = useCallback(async (route: string) => {
    if (!finalConfig.enabled || preloadedRoutes.current.has(route)) {
      return;
    }

    preloadedRoutes.current.add(route);

    const preloadFn = async () => {
      switch (route) {
        case 'chat':
          await preloadComponents.chat();
          break;
        case 'documents':
          await preloadComponents.documents();
          break;
        case 'etl':
          await preloadComponents.etl();
          break;
        case 'profile':
          await preloadComponents.profile();
          break;
        case 'modals':
          await preloadComponents.modals();
          break;
      }
    };

    await executePreload(preloadFn);
  }, [finalConfig.enabled, executePreload]);

  // Preload based on current route
  useEffect(() => {
    if (!finalConfig.enabled) return;

    const targets = getPreloadTargets(pathname);
    
    // Delay preloading to avoid interfering with initial page load
    const timer = setTimeout(() => {
      targets.forEach(target => {
        preloadRoute(target);
      });
    }, finalConfig.preloadDelay);

    return () => clearTimeout(timer);
  }, [pathname, finalConfig.enabled, finalConfig.preloadDelay, getPreloadTargets, preloadRoute]);

  // Preload on idle
  useEffect(() => {
    if (!finalConfig.enabled || !finalConfig.preloadOnIdle) return;

    let idleTimer: NodeJS.Timeout;

    const resetIdleTimer = () => {
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        // Preload modals and less critical components when idle
        preloadRoute('modals');
      }, 5000); // 5 seconds of inactivity
    };

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    
    events.forEach(event => {
      document.addEventListener(event, resetIdleTimer, { passive: true });
    });

    resetIdleTimer();

    return () => {
      clearTimeout(idleTimer);
      events.forEach(event => {
        document.removeEventListener(event, resetIdleTimer);
      });
    };
  }, [finalConfig.enabled, finalConfig.preloadOnIdle, preloadRoute]);

  // Manual preload function for hover/focus events
  const preloadOnInteraction = useCallback((route: string) => {
    if (finalConfig.preloadOnHover) {
      preloadRoute(route);
    }
  }, [finalConfig.preloadOnHover, preloadRoute]);

  return {
    preloadRoute,
    preloadOnInteraction,
    preloadedRoutes: Array.from(preloadedRoutes.current),
    isPreloading: activePreloads.current > 0,
  };
}

/**
 * Hook for navigation link preloading
 */
export function useNavLinkPreloading() {
  const { preloadOnInteraction } = useComponentPreloading();

  const getLinkProps = useCallback((route: string) => ({
    onMouseEnter: () => preloadOnInteraction(route),
    onFocus: () => preloadOnInteraction(route),
  }), [preloadOnInteraction]);

  return { getLinkProps };
}

/**
 * Hook for intersection-based preloading
 */
export function useIntersectionPreloading(
  targetRoute: string,
  options: IntersectionObserverInit = {}
) {
  const { preloadRoute } = useComponentPreloading();
  const observerRef = useRef<IntersectionObserver | null>(null);
  const hasPreloaded = useRef(false);

  const observe = useCallback((element: Element | null) => {
    if (!element || hasPreloaded.current) return;

    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasPreloaded.current) {
          hasPreloaded.current = true;
          preloadRoute(targetRoute);
          observerRef.current?.disconnect();
        }
      },
      { rootMargin: '100px', ...options }
    );

    observerRef.current.observe(element);
  }, [targetRoute, preloadRoute, options]);

  useEffect(() => {
    return () => {
      observerRef.current?.disconnect();
    };
  }, []);

  return { observe };
}

/**
 * Performance monitoring for preloading
 */
export function usePreloadingMetrics() {
  const metricsRef = useRef({
    preloadCount: 0,
    preloadTime: 0,
    cacheHits: 0,
    cacheMisses: 0,
  });

  const recordPreload = useCallback((startTime: number, success: boolean) => {
    const endTime = performance.now();
    const duration = endTime - startTime;

    metricsRef.current.preloadCount++;
    metricsRef.current.preloadTime += duration;

    if (success) {
      metricsRef.current.cacheHits++;
    } else {
      metricsRef.current.cacheMisses++;
    }
  }, []);

  const getMetrics = useCallback(() => {
    const metrics = metricsRef.current;
    return {
      ...metrics,
      averagePreloadTime: metrics.preloadCount > 0 ? metrics.preloadTime / metrics.preloadCount : 0,
      successRate: metrics.preloadCount > 0 ? (metrics.cacheHits / metrics.preloadCount) * 100 : 0,
    };
  }, []);

  const resetMetrics = useCallback(() => {
    metricsRef.current = {
      preloadCount: 0,
      preloadTime: 0,
      cacheHits: 0,
      cacheMisses: 0,
    };
  }, []);

  return {
    recordPreload,
    getMetrics,
    resetMetrics,
  };
}