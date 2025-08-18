/**
 * Chunk Loading Error Handler
 * 
 * Handles Next.js chunk loading failures with retry mechanisms
 * and fallback strategies as specified in requirements 1.1, 1.3, 5.2
 */

interface ChunkLoadError {
  chunkName: string;
  attemptCount: number;
  lastError: Error;
  timestamp: Date;
}

interface ChunkErrorHandlerConfig {
  maxRetries: number;
  retryDelay: number;
  exponentialBackoff: boolean;
  fallbackEnabled: boolean;
}

class ChunkErrorHandler {
  private static instance: ChunkErrorHandler;
  private failedChunks: Map<string, ChunkLoadError> = new Map();
  private config: ChunkErrorHandlerConfig = {
    maxRetries: 3,
    retryDelay: 1000, // 1 second
    exponentialBackoff: true,
    fallbackEnabled: true,
  };

  private constructor() {
    this.setupGlobalErrorHandlers();
  }

  static getInstance(): ChunkErrorHandler {
    if (!ChunkErrorHandler.instance) {
      ChunkErrorHandler.instance = new ChunkErrorHandler();
    }
    return ChunkErrorHandler.instance;
  }

  /**
   * Setup global error handlers for chunk loading failures
   */
  private setupGlobalErrorHandlers(): void {
    if (typeof window === 'undefined') return;

    // Handle script loading errors
    window.addEventListener('error', (event) => {
      if (this.isChunkLoadError(event)) {
        this.handleChunkError(event);
      }
    });

    // Handle unhandled promise rejections (for dynamic imports)
    window.addEventListener('unhandledrejection', (event) => {
      if (this.isChunkLoadRejection(event)) {
        this.handleChunkRejection(event);
      }
    });
  }

  /**
   * Check if error is a chunk loading error
   */
  private isChunkLoadError(event: ErrorEvent): boolean {
    const target = event.target as HTMLScriptElement;
    return (
      target &&
      target.tagName === 'SCRIPT' &&
      target.src &&
      (target.src.includes('/_next/static/chunks/') || 
       target.src.includes('/_next/static/js/'))
    );
  }

  /**
   * Check if promise rejection is related to chunk loading
   */
  private isChunkLoadRejection(event: PromiseRejectionEvent): boolean {
    const reason = event.reason;
    return (
      reason &&
      typeof reason === 'object' &&
      (reason.message?.includes('Loading chunk') ||
       reason.message?.includes('Loading CSS chunk') ||
       reason.code === 'ChunkLoadError')
    );
  }

  /**
   * Handle chunk loading error from script tag
   */
  private async handleChunkError(event: ErrorEvent): Promise<void> {
    const target = event.target as HTMLScriptElement;
    const chunkName = this.extractChunkName(target.src);
    
    console.warn(`Chunk loading failed: ${chunkName}`, event);
    
    const shouldRetry = await this.recordFailureAndCheckRetry(chunkName, new Error(`Failed to load chunk: ${chunkName}`));
    
    if (shouldRetry) {
      await this.retryChunkLoad(chunkName, target.src);
    } else {
      this.handleFallback(chunkName);
    }
  }

  /**
   * Handle chunk loading rejection from dynamic import
   */
  private async handleChunkRejection(event: PromiseRejectionEvent): Promise<void> {
    const error = event.reason;
    const chunkName = this.extractChunkNameFromError(error);
    
    console.warn(`Chunk loading rejected: ${chunkName}`, error);
    
    const shouldRetry = await this.recordFailureAndCheckRetry(chunkName, error);
    
    if (shouldRetry) {
      // For dynamic imports, we can't directly retry, but we can trigger a page reload
      // or notify the application to retry the import
      this.notifyChunkRetryNeeded(chunkName);
    } else {
      this.handleFallback(chunkName);
    }
  }

  /**
   * Extract chunk name from script URL
   */
  private extractChunkName(url: string): string {
    const match = url.match(/\/_next\/static\/(?:chunks|js)\/(.+?)(?:\?|$)/);
    return match ? match[1] : url;
  }

  /**
   * Extract chunk name from error message
   */
  private extractChunkNameFromError(error: any): string {
    if (error.message) {
      const match = error.message.match(/Loading chunk (\d+)/);
      if (match) return `chunk-${match[1]}`;
      
      const cssMatch = error.message.match(/Loading CSS chunk (\d+)/);
      if (cssMatch) return `css-chunk-${cssMatch[1]}`;
    }
    return 'unknown-chunk';
  }

  /**
   * Record failure and determine if retry should be attempted
   */
  private async recordFailureAndCheckRetry(chunkName: string, error: Error): Promise<boolean> {
    const existing = this.failedChunks.get(chunkName);
    
    if (existing) {
      existing.attemptCount++;
      existing.lastError = error;
      existing.timestamp = new Date();
    } else {
      this.failedChunks.set(chunkName, {
        chunkName,
        attemptCount: 1,
        lastError: error,
        timestamp: new Date(),
      });
    }

    const failure = this.failedChunks.get(chunkName)!;
    return failure.attemptCount <= this.config.maxRetries;
  }

  /**
   * Retry loading a specific chunk
   */
  private async retryChunkLoad(chunkName: string, originalUrl: string): Promise<boolean> {
    const failure = this.failedChunks.get(chunkName);
    if (!failure) return false;

    const delay = this.calculateRetryDelay(failure.attemptCount);
    
    console.log(`Retrying chunk load for ${chunkName} in ${delay}ms (attempt ${failure.attemptCount})`);
    
    await this.sleep(delay);

    try {
      // Create a new script element to retry loading
      const script = document.createElement('script');
      script.src = originalUrl;
      script.async = true;
      
      return new Promise<boolean>((resolve) => {
        script.onload = () => {
          console.log(`Successfully retried chunk: ${chunkName}`);
          this.failedChunks.delete(chunkName);
          document.head.removeChild(script);
          resolve(true);
        };
        
        script.onerror = () => {
          console.error(`Retry failed for chunk: ${chunkName}`);
          document.head.removeChild(script);
          resolve(false);
        };
        
        document.head.appendChild(script);
      });
    } catch (error) {
      console.error(`Error during chunk retry for ${chunkName}:`, error);
      return false;
    }
  }

  /**
   * Calculate retry delay with optional exponential backoff
   */
  private calculateRetryDelay(attemptCount: number): number {
    if (!this.config.exponentialBackoff) {
      return this.config.retryDelay;
    }
    
    // Exponential backoff: 1s, 2s, 4s, 8s...
    return this.config.retryDelay * Math.pow(2, attemptCount - 1);
  }

  /**
   * Sleep utility for retry delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Notify application that a chunk retry is needed
   */
  private notifyChunkRetryNeeded(chunkName: string): void {
    window.dispatchEvent(new CustomEvent('chunk:retry-needed', {
      detail: { chunkName, failure: this.failedChunks.get(chunkName) }
    }));
  }

  /**
   * Handle fallback when all retries are exhausted
   */
  private handleFallback(chunkName: string): void {
    if (!this.config.fallbackEnabled) return;

    console.error(`All retries exhausted for chunk: ${chunkName}. Triggering fallback.`);
    
    // Dispatch event for application to handle
    window.dispatchEvent(new CustomEvent('chunk:fallback', {
      detail: { chunkName, failure: this.failedChunks.get(chunkName) }
    }));

    // For critical chunks, trigger a page reload as last resort
    if (this.isCriticalChunk(chunkName)) {
      this.triggerPageReload(chunkName);
    }
  }

  /**
   * Check if chunk is critical for application functionality
   */
  private isCriticalChunk(chunkName: string): boolean {
    const criticalPatterns = [
      'main',
      'app',
      'layout',
      'page',
      '_app',
      'framework',
    ];
    
    return criticalPatterns.some(pattern => 
      chunkName.toLowerCase().includes(pattern)
    );
  }

  /**
   * Trigger page reload as last resort for critical chunks
   */
  private triggerPageReload(chunkName: string): void {
    console.warn(`Critical chunk ${chunkName} failed to load. Reloading page...`);
    
    // Add a small delay to allow error reporting
    setTimeout(() => {
      window.location.reload();
    }, 2000);
  }

  /**
   * Get current failure statistics
   */
  public getFailureStats(): ChunkLoadError[] {
    return Array.from(this.failedChunks.values());
  }

  /**
   * Clear failure history
   */
  public clearFailureHistory(): void {
    this.failedChunks.clear();
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<ChunkErrorHandlerConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * Manual retry for a specific chunk (for use in UI)
   */
  public async manualRetry(chunkName: string): Promise<boolean> {
    const failure = this.failedChunks.get(chunkName);
    if (!failure) return false;

    // Reset attempt count for manual retry
    failure.attemptCount = 0;
    
    // Try to reconstruct the URL (this is a best effort)
    const url = `/_next/static/chunks/${chunkName}`;
    return this.retryChunkLoad(chunkName, url);
  }
}

// Export singleton instance
export const chunkErrorHandler = ChunkErrorHandler.getInstance();

// Export types for use in components
export type { ChunkLoadError, ChunkErrorHandlerConfig };

// Initialize chunk error handler when module is imported
if (typeof window !== 'undefined') {
  chunkErrorHandler;
}