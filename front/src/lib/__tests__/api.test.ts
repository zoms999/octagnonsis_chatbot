import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { ApiClient, TokenManager, ApiErrorHandler } from '../api';
import { LoginCredentials, AuthUser, ChatResponse, ChatFeedback } from '../types';

// Mock fetch globally
global.fetch = vi.fn();

describe('TokenManager', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  it('should store and retrieve tokens', () => {
    const accessToken = 'test-access-token';
    const refreshToken = 'test-refresh-token';

    TokenManager.setTokens(accessToken, refreshToken);

    expect(TokenManager.getAccessToken()).toBe(accessToken);
    expect(TokenManager.getRefreshToken()).toBe(refreshToken);
    expect(TokenManager.isAuthenticated()).toBe(true);
  });

  it('should clear tokens', () => {
    TokenManager.setTokens('access', 'refresh');
    TokenManager.clearTokens();

    expect(TokenManager.getAccessToken()).toBeNull();
    expect(TokenManager.getRefreshToken()).toBeNull();
    expect(TokenManager.isAuthenticated()).toBe(false);
  });
});

describe('ApiErrorHandler', () => {
  it('should create auth error for 401 status', () => {
    const response = new Response('Unauthorized', { status: 401 });
    const error = ApiErrorHandler.createError(response);

    expect(error.status).toBe(401);
    expect((error as any).type).toBe('auth_error');
  });

  it('should create rate limit error for 429 status', () => {
    const response = new Response('Too Many Requests', { status: 429 });
    const error = ApiErrorHandler.createError(response, { retry_after: 60 });

    expect(error.status).toBe(429);
    expect((error as any).type).toBe('rate_limit');
    expect((error as any).retry_after).toBe(60);
  });

  it('should create validation error for 400 status', () => {
    const response = new Response('Bad Request', { status: 400 });
    const fieldErrors = { username: ['This field is required'] };
    const error = ApiErrorHandler.createError(response, { field_errors: fieldErrors });

    expect(error.status).toBe(400);
    expect((error as any).type).toBe('validation_error');
    expect((error as any).field_errors).toEqual(fieldErrors);
  });

  it('should identify error types correctly', () => {
    const authError = { type: 'auth_error', status: 401 };
    const rateLimitError = { type: 'rate_limit', status: 429 };
    const validationError = { type: 'validation_error', status: 400 };
    const serverError = { type: 'server_error', status: 500 };
    const networkError = new TypeError('Failed to fetch');

    expect(ApiErrorHandler.isAuthError(authError)).toBe(true);
    expect(ApiErrorHandler.isRateLimitError(rateLimitError)).toBe(true);
    expect(ApiErrorHandler.isValidationError(validationError)).toBe(true);
    expect(ApiErrorHandler.isServerError(serverError)).toBe(true);
    expect(ApiErrorHandler.isNetworkError(networkError)).toBe(true);
  });
});

describe('ApiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    
    // Mock window for event dispatching
    vi.stubGlobal('window', {
      dispatchEvent: vi.fn(),
      location: { pathname: '/chat', href: '' },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should login successfully and store tokens', async () => {
    const mockResponse = {
      user: { id: '1', name: 'Test User', type: 'personal' } as AuthUser,
      tokens: { access: 'access-token', refresh: 'refresh-token' },
      expires_at: '2024-01-01T00:00:00Z'
    };

    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    const credentials: LoginCredentials = {
      username: 'testuser',
      password: 'password',
      loginType: 'personal'
    };

    const result = await ApiClient.login(credentials);

    expect(result).toEqual(mockResponse);
    expect(TokenManager.getAccessToken()).toBe('access-token');
    expect(TokenManager.getRefreshToken()).toBe('refresh-token');
  });

  it('should include Bearer token in requests', async () => {
    TokenManager.setTokens('test-token', 'refresh-token');

    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: '1', name: 'Test User' }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    await ApiClient.validateSession();

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/auth/me'),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': 'Bearer test-token'
        })
      })
    );
  });

  it('should handle network errors', async () => {
    (fetch as any).mockRejectedValueOnce(new TypeError('Failed to fetch'));

    await expect(ApiClient.validateSession()).rejects.toMatchObject({
      message: 'Network error. Please check your connection.',
      status: 0,
      code: 'NETWORK_ERROR'
    });
  });

  it('should handle API errors', async () => {
    (fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ message: 'Invalid credentials' }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    await expect(ApiClient.validateSession()).rejects.toMatchObject({
      message: 'Invalid credentials',
      status: 401,
      type: 'auth_error'
    });
  });

  it('should handle 401 errors by clearing tokens and dispatching logout event', async () => {
    TokenManager.setTokens('invalid-token', 'refresh-token');

    (fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ message: 'Token expired' }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    await expect(ApiClient.validateSession()).rejects.toMatchObject({
      status: 401,
      type: 'auth_error'
    });

    // TokenManager.clearTokens is called internally by the API client
    expect(window.dispatchEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'auth:logout',
        detail: expect.objectContaining({
          reason: '401_unauthorized'
        })
      })
    );
  });

  it('should retry requests on retryable errors', async () => {
    // First call fails with 500, second succeeds
    (fetch as any)
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ message: 'Server error' }),
        headers: new Headers({ 'content-type': 'application/json' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: '1', name: 'Test User' }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

    const result = await ApiClient.validateSession();
    expect(result).toEqual({ id: '1', name: 'Test User' });
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it('should handle rate limiting with retry after', async () => {
    (fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 429,
      statusText: 'Too Many Requests',
      json: async () => ({ message: 'Rate limited', retry_after: 1 }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });

    await expect(ApiClient.validateSession()).rejects.toMatchObject({
      status: 429,
      type: 'rate_limit'
    });
  });

  describe('Chat endpoints', () => {
    it('should send question successfully', async () => {
      const mockResponse: ChatResponse = {
        conversation_id: 'conv-123',
        response: 'Test response',
        retrieved_documents: [],
        confidence_score: 0.95,
        processing_time: 1.5,
        timestamp: '2024-01-01T00:00:00Z'
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await ApiClient.sendQuestion('Test question', 'conv-123');
      
      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/chat/question'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            question: 'Test question',
            conversation_id: 'conv-123'
          })
        })
      );
    });

    it('should submit feedback successfully', async () => {
      const feedback: ChatFeedback = {
        conversation_id: 'conv-123',
        message_id: 'msg-456',
        rating: 5,
        helpful: true,
        comments: 'Great response!'
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await ApiClient.submitFeedback(feedback);
      
      expect(result).toEqual({ success: true });
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/chat/feedback'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(feedback)
        })
      );
    });
  });

  describe('ETL endpoints', () => {
    it('should get ETL jobs with pagination', async () => {
      const mockResponse = {
        jobs: [{ job_id: 'job-123', status: 'completed' }],
        total: 1,
        page: 1,
        limit: 20
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await ApiClient.getETLJobs('user-123', 1, 20);
      
      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/etl/users/user-123/jobs?page=1&limit=20'),
        expect.any(Object)
      );
    });

    it('should retry ETL job', async () => {
      const mockResponse = {
        job_id: 'job-123',
        progress_url: '/api/etl/jobs/job-123/progress',
        estimated_completion_time: '2024-01-01T01:00:00Z'
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await ApiClient.retryETLJob('job-123');
      
      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/etl/jobs/job-123/retry'),
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('User management endpoints', () => {
    it('should get user profile', async () => {
      const mockProfile = {
        user_id: 'user-123',
        document_count: 5,
        conversation_count: 10,
        available_document_types: ['primary_tendency', 'top_skills'],
        last_conversation_at: '2024-01-01T00:00:00Z',
        processing_status: 'completed'
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockProfile,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await ApiClient.getUserProfile('user-123');
      
      expect(result).toEqual(mockProfile);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/users/user-123/profile'),
        expect.any(Object)
      );
    });

    it('should get user documents with filtering', async () => {
      const mockResponse = {
        documents: [{ id: 'doc-123', doc_type: 'primary_tendency' }],
        total: 1,
        page: 1,
        limit: 20
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await ApiClient.getUserDocuments('user-123', 1, 20, 'primary_tendency');
      
      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/users/user-123/documents?page=1&limit=20&doc_type=primary_tendency'),
        expect.any(Object)
      );
    });
  });

  describe('Error handling edge cases', () => {
    it('should handle timeout errors', async () => {
      const timeoutError = new DOMException('The operation was aborted', 'AbortError');
      (fetch as any).mockRejectedValueOnce(timeoutError);

      await expect(ApiClient.validateSession()).rejects.toMatchObject({
        message: 'Request timed out. Please try again.',
        status: 0,
        code: 'TIMEOUT_ERROR',
        type: 'network_error'
      });
    });

    it('should handle non-JSON responses', async () => {
      (fetch as any).mockResolvedValueOnce({
        ok: true,
        text: async () => 'Plain text response',
        headers: new Headers({ 'content-type': 'text/plain' }),
      });

      const result = await ApiClient.validateSession();
      expect(result).toBe('Plain text response');
    });

    it('should not retry on validation errors', async () => {
      (fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ message: 'Validation failed' }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      await expect(ApiClient.validateSession()).rejects.toMatchObject({
        status: 400,
        type: 'validation_error'
      });

      expect(fetch).toHaveBeenCalledTimes(1); // No retry
    });
  });
});