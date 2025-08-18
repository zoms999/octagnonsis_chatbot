import { Page } from '@playwright/test';
import { mockApiResponses } from '../fixtures/test-data';

/**
 * Mock server utilities for intercepting API calls during E2E tests
 */
export class MockServer {
  constructor(private page: Page) {}

  /**
   * Mock authentication endpoints
   */
  async mockAuthEndpoints() {
    // Mock login endpoint
    await this.page.route('**/api/auth/login', async (route) => {
      const request = route.request();
      const postData = request.postDataJSON();
      
      if (postData.username && postData.password) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockApiResponses.loginSuccess),
        });
      } else {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Invalid credentials' }),
        });
      }
    });

    // Mock auth validation endpoint
    await this.page.route('**/api/auth/me', async (route) => {
      const authHeader = route.request().headers()['authorization'];
      
      if (authHeader && authHeader.includes('Bearer')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockApiResponses.loginSuccess.user),
        });
      } else {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Unauthorized' }),
        });
      }
    });

    // Mock logout endpoint
    await this.page.route('**/api/auth/logout', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Logged out successfully' }),
      });
    });
  }

  /**
   * Mock chat endpoints
   */
  async mockChatEndpoints() {
    // Mock chat question endpoint (HTTP fallback)
    await this.page.route('**/api/chat/question', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate processing time
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockApiResponses.chatResponse),
      });
    });

    // Mock conversation history endpoint
    await this.page.route('**/api/chat/history/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockApiResponses.conversationHistory),
      });
    });

    // Mock feedback endpoint
    await this.page.route('**/api/chat/feedback', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Feedback submitted successfully' }),
      });
    });
  }

  /**
   * Mock ETL endpoints
   */
  async mockETLEndpoints() {
    // Mock ETL jobs list
    await this.page.route('**/api/etl/users/*/jobs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockApiResponses.etlJobs),
      });
    });

    // Mock ETL job status
    await this.page.route('**/api/etl/jobs/*/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockApiResponses.etlJobs.jobs[0]),
      });
    });

    // Mock ETL job retry
    await this.page.route('**/api/etl/jobs/*/retry', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Job retry initiated' }),
      });
    });

    // Mock ETL reprocess
    await this.page.route('**/api/etl/users/*/reprocess', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ 
          job_id: 'job-new-123',
          message: 'Reprocessing initiated' 
        }),
      });
    });
  }

  /**
   * Mock user management endpoints
   */
  async mockUserEndpoints() {
    // Mock user profile
    await this.page.route('**/api/users/*/profile', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockApiResponses.userProfile),
      });
    });

    // Mock user documents
    await this.page.route('**/api/users/*/documents', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockApiResponses.userDocuments),
      });
    });
  }

  /**
   * Mock WebSocket connection
   */
  async mockWebSocket() {
    // Intercept WebSocket connections and simulate responses
    await this.page.addInitScript(() => {
      // Override WebSocket constructor
      const OriginalWebSocket = window.WebSocket;
      
      class MockWebSocket extends EventTarget {
        public readyState = WebSocket.CONNECTING;
        public url: string;
        
        constructor(url: string) {
          super();
          this.url = url;
          
          // Simulate connection opening
          setTimeout(() => {
            this.readyState = WebSocket.OPEN;
            this.dispatchEvent(new Event('open'));
          }, 100);
        }
        
        send(data: string) {
          const message = JSON.parse(data);
          
          // Simulate processing status
          setTimeout(() => {
            this.dispatchEvent(new MessageEvent('message', {
              data: JSON.stringify({
                type: 'status',
                data: { status: 'processing', progress: 50 }
              })
            }));
          }, 500);
          
          // Simulate response
          setTimeout(() => {
            this.dispatchEvent(new MessageEvent('message', {
              data: JSON.stringify({
                type: 'response',
                data: {
                  conversation_id: 'conv-123',
                  response: 'Based on your aptitude test results, you show strong analytical skills...',
                  retrieved_documents: [{
                    id: 'doc-1',
                    type: 'primary_tendency',
                    title: 'Primary Aptitude Analysis',
                    preview: 'Your primary tendency shows...',
                    relevance_score: 0.95,
                  }],
                  confidence_score: 0.87,
                  processing_time: 1.2,
                  timestamp: new Date().toISOString(),
                }
              })
            }));
          }, 2000);
        }
        
        close() {
          this.readyState = WebSocket.CLOSED;
          this.dispatchEvent(new Event('close'));
        }
      }
      
      // Replace WebSocket with mock
      (window as any).WebSocket = MockWebSocket;
    });
  }

  /**
   * Mock Server-Sent Events for ETL progress
   */
  async mockServerSentEvents() {
    await this.page.addInitScript(() => {
      // Override EventSource constructor
      class MockEventSource extends EventTarget {
        public readyState = EventSource.CONNECTING;
        public url: string;
        
        constructor(url: string) {
          super();
          this.url = url;
          
          // Simulate connection opening
          setTimeout(() => {
            this.readyState = EventSource.OPEN;
            this.dispatchEvent(new Event('open'));
            
            // Simulate progress updates
            let progress = 0;
            const interval = setInterval(() => {
              progress += 10;
              
              this.dispatchEvent(new MessageEvent('progress', {
                data: JSON.stringify({
                  progress,
                  current_step: `Processing step ${Math.floor(progress / 10)}`,
                  estimated_completion_time: new Date(Date.now() + (100 - progress) * 1000).toISOString(),
                })
              }));
              
              if (progress >= 100) {
                clearInterval(interval);
                this.dispatchEvent(new MessageEvent('complete', {
                  data: JSON.stringify({
                    status: 'completed',
                    message: 'ETL job completed successfully'
                  })
                }));
              }
            }, 500);
          }, 100);
        }
        
        close() {
          this.readyState = EventSource.CLOSED;
          this.dispatchEvent(new Event('close'));
        }
      }
      
      // Replace EventSource with mock
      (window as any).EventSource = MockEventSource;
    });
  }

  /**
   * Setup all mocks for comprehensive testing
   */
  async setupAllMocks() {
    await this.mockAuthEndpoints();
    await this.mockChatEndpoints();
    await this.mockETLEndpoints();
    await this.mockUserEndpoints();
    await this.mockWebSocket();
    await this.mockServerSentEvents();
  }

  /**
   * Simulate network errors for error handling tests
   */
  async simulateNetworkError(endpoint: string) {
    await this.page.route(endpoint, async (route) => {
      await route.abort('failed');
    });
  }

  /**
   * Simulate rate limiting
   */
  async simulateRateLimit(endpoint: string) {
    await this.page.route(endpoint, async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ 
          error: 'Rate limit exceeded',
          retry_after: 60 
        }),
      });
    });
  }

  /**
   * Restore network connectivity after simulating errors
   */
  async restoreNetwork() {
    await this.page.unrouteAll();
    await this.setupAllMocks();
  }

  /**
   * Clear all mocks
   */
  async clearAllMocks() {
    await this.page.unrouteAll();
  }
}