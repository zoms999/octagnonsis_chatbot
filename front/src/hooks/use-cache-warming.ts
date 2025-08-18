import { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/providers/auth-provider';
import { cacheUtils } from '@/lib/react-query';

/**
 * Hook for intelligent cache warming based on user navigation patterns
 */
export function useCacheWarming() {
  const { user } = useAuth();
  const router = useRouter();

  // Warm cache for likely next routes
  const warmCacheForRoute = useCallback(async (currentRoute: string) => {
    if (!user?.id) return;

    const routeMap: Record<string, string[]> = {
      '/chat': ['/history', '/profile'], // From chat, users often go to history or profile
      '/history': ['/chat', '/profile'], // From history, users often go back to chat
      '/profile': ['/documents', '/etl'], // From profile, users check documents or ETL
      '/documents': ['/etl', '/profile'], // From documents, users check ETL status
      '/etl': ['/documents', '/profile'], // From ETL, users check documents or profile
    };

    const nextRoutes = routeMap[currentRoute] || [];
    if (nextRoutes.length > 0) {
      await cacheUtils.warmCache(nextRoutes, user.id);
    }
  }, [user?.id]);

  // Preload critical data on user authentication
  useEffect(() => {
    if (user?.id) {
      cacheUtils.preloadCriticalData(user.id);
    }
  }, [user?.id]);

  return {
    warmCacheForRoute,
  };
}

/**
 * Hook for route-specific cache warming
 */
export function useRouteBasedCaching(currentRoute: string) {
  const { user } = useAuth();
  const { warmCacheForRoute } = useCacheWarming();

  useEffect(() => {
    // Warm cache for likely next routes after a delay
    const timer = setTimeout(() => {
      warmCacheForRoute(currentRoute);
    }, 2000); // Wait 2 seconds after route load

    return () => clearTimeout(timer);
  }, [currentRoute, warmCacheForRoute]);

  // Prefetch data specific to current route
  useEffect(() => {
    if (!user?.id) return;

    const prefetchForRoute = async () => {
      switch (currentRoute) {
        case '/chat':
          // Prefetch recent conversations for quick access
          await cacheUtils.warmCache(['/history'], user.id);
          break;
        case '/profile':
          // Prefetch documents and ETL data
          await cacheUtils.warmCache(['/documents', '/etl'], user.id);
          break;
        case '/documents':
          // Prefetch ETL status for document processing info
          await cacheUtils.warmCache(['/etl'], user.id);
          break;
        case '/etl':
          // Prefetch user profile for processing status
          await cacheUtils.warmCache(['/profile'], user.id);
          break;
      }
    };

    prefetchForRoute();
  }, [currentRoute, user?.id]);
}

/**
 * Hook for background data refresh
 */
export function useBackgroundRefresh() {
  const { user } = useAuth();

  useEffect(() => {
    if (!user?.id) return;

    // Set up background refresh for critical data
    const intervals: NodeJS.Timeout[] = [];

    // Refresh user profile every 10 minutes
    intervals.push(
      setInterval(() => {
        cacheUtils.prefetchUserData(user.id, 'normal');
      }, 10 * 60 * 1000)
    );

    // Refresh ETL jobs every 30 seconds if user is on ETL page
    if (typeof window !== 'undefined' && window.location.pathname === '/etl') {
      intervals.push(
        setInterval(() => {
          cacheUtils.warmCache(['/etl'], user.id);
        }, 30 * 1000)
      );
    }

    return () => {
      intervals.forEach(clearInterval);
    };
  }, [user?.id]);
}

/**
 * Hook for intelligent prefetching based on user behavior
 */
export function useIntelligentPrefetching() {
  const { user } = useAuth();

  const prefetchBasedOnTime = useCallback(() => {
    if (!user?.id) return;

    const hour = new Date().getHours();
    
    // Morning (6-12): Users likely to check profile and documents
    if (hour >= 6 && hour < 12) {
      cacheUtils.warmCache(['/profile', '/documents'], user.id);
    }
    // Afternoon (12-18): Users likely to use chat and check history
    else if (hour >= 12 && hour < 18) {
      cacheUtils.warmCache(['/chat', '/history'], user.id);
    }
    // Evening (18-22): Users likely to review ETL and documents
    else if (hour >= 18 && hour < 22) {
      cacheUtils.warmCache(['/etl', '/documents'], user.id);
    }
  }, [user?.id]);

  const prefetchBasedOnActivity = useCallback((lastActivity: string) => {
    if (!user?.id) return;

    // If user was recently active in chat, prefetch related data
    if (lastActivity === 'chat') {
      cacheUtils.warmCache(['/history', '/profile'], user.id);
    }
    // If user was checking documents, prefetch ETL status
    else if (lastActivity === 'documents') {
      cacheUtils.warmCache(['/etl'], user.id);
    }
  }, [user?.id]);

  useEffect(() => {
    // Initial prefetch based on time of day
    prefetchBasedOnTime();

    // Set up periodic intelligent prefetching
    const interval = setInterval(prefetchBasedOnTime, 30 * 60 * 1000); // Every 30 minutes

    return () => clearInterval(interval);
  }, [prefetchBasedOnTime]);

  return {
    prefetchBasedOnActivity,
  };
}