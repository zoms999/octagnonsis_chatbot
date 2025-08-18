import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Simple integration test to verify lazy loading works
describe('Lazy Loading Integration', () => {
  it('should support React.lazy components', async () => {
    const LazyComponent = React.lazy(() => 
      Promise.resolve({ 
        default: () => <div data-testid="lazy-loaded">Lazy Loaded!</div> 
      })
    );

    render(
      <React.Suspense fallback={<div data-testid="loading">Loading...</div>}>
        <LazyComponent />
      </React.Suspense>
    );

    // Should eventually show the lazy component
    expect(await screen.findByTestId('lazy-loaded')).toBeInTheDocument();
  });

  it('should show fallback during loading', () => {
    const LazyComponent = React.lazy(() => 
      new Promise(() => {}) // Never resolves
    );

    render(
      <React.Suspense fallback={<div data-testid="loading">Loading...</div>}>
        <LazyComponent />
      </React.Suspense>
    );

    // Should show loading fallback
    expect(screen.getByTestId('loading')).toBeInTheDocument();
  });
});