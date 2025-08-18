'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState, ReactNode } from 'react';
import { queryClient, devToolsConfig } from '@/lib/react-query';
import { usePerformanceMonitoring, useAutoOptimization, usePerformanceDebugger } from '@/hooks/use-performance-monitoring';

interface ReactQueryProviderProps {
  children: ReactNode;
}

function PerformanceMonitor() {
  // Enable performance monitoring in development
  usePerformanceMonitoring(process.env.NODE_ENV === 'development');
  
  // Enable auto-optimization in all environments
  useAutoOptimization(true);
  
  // Enable performance debugger in development
  usePerformanceDebugger();
  
  return null;
}

export function ReactQueryProvider({ children }: ReactQueryProviderProps) {
  // Use a state to ensure the QueryClient is only created once per component instance
  const [client] = useState(() => queryClient);

  return (
    <QueryClientProvider client={client}>
      <PerformanceMonitor />
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools 
          initialIsOpen={devToolsConfig.initialIsOpen}
        />
      )}
    </QueryClientProvider>
  );
}

export default ReactQueryProvider;