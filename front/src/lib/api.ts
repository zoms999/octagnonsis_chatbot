import { 
  ApiResponse, 
  ApiError, 
  LoginCredentials, 
  LoginResponse, 
  ChatResponse, 
  ChatFeedback, 
  ChatFeedbackResponse,
  ConversationHistoryResponse,
  ConversationDetail,
  ETLJobsResponse,
  ETLJobStatusResponse,
  ETLJobResponse,
  UserProfileResponse,
  UserDocumentsResponse,
  AuthUser,
  NetworkError,
  AuthError,
  RateLimitError,
  ValidationError,
  ServerError
} from './types';
import { SecureTokenManager } from './auth';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
const ADMIN_TOKEN = process.env.NEXT_PUBLIC_ADMIN_TOKEN;

// Use SecureTokenManager from auth utilities
const TokenManager = SecureTokenManager;

// Error handling utilities
export class ApiErrorHandler {
  static createError(response: Response, data?: any): ApiError {
    const baseError = {
      message: data?.message || response.statusText || 'An error occurred',
      status: response.status,
      code: data?.code,
      details: data?.details
    };

    switch (response.status) {
      case 401:
        return { ...baseError, type: 'auth_error' } as AuthError;
      case 429:
        return { 
          ...baseError, 
          type: 'rate_limit',
          retry_after: data?.retry_after 
        } as RateLimitError;
      case 400:
        return { 
          ...baseError, 
          type: 'validation_error',
          field_errors: data?.field_errors 
        } as ValidationError;
      case 500:
      case 502:
      case 503:
      case 504:
        return { ...baseError, type: 'server_error' } as ServerError;
      default:
        return baseError;
    }
  }

  static isNetworkError(error: any): error is NetworkError {
    return error instanceof TypeError && error.message.includes('fetch');
  }

  static isAuthError(error: any): error is AuthError {
    return error.type === 'auth_error' || error.status === 401;
  }

  static isRateLimitError(error: any): error is RateLimitError {
    return error.type === 'rate_limit' || error.status === 429;
  }

  static isValidationError(error: any): error is ValidationError {
    return error.type === 'validation_error' || error.status === 400;
  }

  static isServerError(error: any): error is ServerError {
    return error.type === 'server_error' || (error.status >= 500 && error.status < 600);
  }

  static isApiError(error: any): error is ApiError {
    return error && typeof error === 'object' && 'status' in error;
  }

  static isRetryableError(error: any): boolean {
    return this.isNetworkError(error) || 
           this.isServerError(error) || 
           this.isRateLimitError(error);
  }
}

// HTTP Client with automatic token injection and retry logic
class HttpClient {
  private baseURL: string;
  private defaultRetries: number = 3;
  private defaultRetryDelay: number = 1000;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  private async requestWithRetry<T>(
    endpoint: string,
    options: RequestInit = {},
    retries: number = this.defaultRetries
  ): Promise<T> {
    let lastError: any;
    
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        return await this.request<T>(endpoint, options);
      } catch (error) {
        lastError = error;
        
        // Don't retry on auth or validation errors
        if (ApiErrorHandler.isAuthError(error) || ApiErrorHandler.isValidationError(error)) {
          throw error;
        }
        
        // Don't retry on the last attempt
        if (attempt === retries) {
          throw error;
        }
        
        // Only retry on network errors, server errors, or rate limits
        if (!ApiErrorHandler.isRetryableError(error)) {
          throw error;
        }
        
        // Handle rate limit errors with proper delay
        if (ApiErrorHandler.isRateLimitError(error)) {
          const rateLimitError = error as RateLimitError;
          const delay = (rateLimitError.retry_after || 60) * 1000;
          console.log(`[API] Rate limited, waiting ${delay}ms before retry ${attempt + 1}/${retries}`);
          await this.delay(delay);
          continue;
        }
        
        // Exponential backoff for other retryable errors
        const delay = this.defaultRetryDelay * Math.pow(2, attempt);
        console.log(`[API] Request failed, retrying in ${delay}ms (attempt ${attempt + 1}/${retries})`);
        await this.delay(delay);
      }
    }
    
    throw lastError;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    // Prepare headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    // Add Bearer token if available
    const accessToken = TokenManager.getAccessToken();
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    // Add admin token if available and needed
    if (ADMIN_TOKEN) {
      headers['X-Admin-Token'] = ADMIN_TOKEN;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      // Handle different response types
      let data: any;
      const contentType = response.headers.get('content-type');
      
      if (contentType?.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        // Handle 401 errors by clearing tokens and triggering logout
        if (response.status === 401) {
          console.warn('[API] 401 Unauthorized - clearing tokens and triggering logout');
          TokenManager.clearTokens();
          
          // Trigger logout in auth context if available
          if (typeof window !== 'undefined') {
            // Dispatch custom event for auth provider to handle
            window.dispatchEvent(new CustomEvent('auth:logout', {
              detail: { reason: '401_unauthorized', endpoint }
            }));
            
            // Only redirect if not already on login page or if this is a user-initiated request
            const currentPath = window.location.pathname;
            if (!currentPath.startsWith('/login')) {
              // Use a small delay to allow auth provider to handle the logout first
              setTimeout(() => {
                const loginUrl = `/login?returnTo=${encodeURIComponent(currentPath)}`;
                window.location.href = loginUrl;
              }, 100);
            }
          }
        }
        
        throw ApiErrorHandler.createError(response, data);
      }

      return data;
    } catch (error) {
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        const networkError = new Error('Network error. Please check your connection.') as NetworkError;
        networkError.status = 0;
        networkError.code = 'NETWORK_ERROR';
        networkError.type = 'network_error';
        throw networkError;
      }
      
      // Handle timeout errors
      if (error instanceof DOMException && error.name === 'AbortError') {
        const timeoutError = new Error('Request timed out. Please try again.') as NetworkError;
        timeoutError.status = 0;
        timeoutError.code = 'TIMEOUT_ERROR';
        timeoutError.type = 'network_error';
        throw timeoutError;
      }
      
      throw error;
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async get<T>(endpoint: string, params?: Record<string, any>, options?: { retries?: number; timeout?: number }): Promise<T> {
    const url = new URL(`${this.baseURL}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }
    
    const requestOptions: RequestInit = {};
    
    // Add timeout if specified
    if (options?.timeout) {
      const controller = new AbortController();
      setTimeout(() => controller.abort(), options.timeout);
      requestOptions.signal = controller.signal;
    }
    
    return this.requestWithRetry<T>(url.pathname + url.search, requestOptions, options?.retries);
  }

  async post<T>(endpoint: string, data?: any, options?: { retries?: number; timeout?: number }): Promise<T> {
    const requestOptions: RequestInit = {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    };
    
    // Add timeout if specified
    if (options?.timeout) {
      const controller = new AbortController();
      setTimeout(() => controller.abort(), options.timeout);
      requestOptions.signal = controller.signal;
    }
    
    return this.requestWithRetry<T>(endpoint, requestOptions, options?.retries);
  }

  async put<T>(endpoint: string, data?: any, options?: { retries?: number; timeout?: number }): Promise<T> {
    const requestOptions: RequestInit = {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    };
    
    if (options?.timeout) {
      const controller = new AbortController();
      setTimeout(() => controller.abort(), options.timeout);
      requestOptions.signal = controller.signal;
    }
    
    return this.requestWithRetry<T>(endpoint, requestOptions, options?.retries);
  }

  async patch<T>(endpoint: string, data?: any, options?: { retries?: number; timeout?: number }): Promise<T> {
    const requestOptions: RequestInit = {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    };
    
    if (options?.timeout) {
      const controller = new AbortController();
      setTimeout(() => controller.abort(), options.timeout);
      requestOptions.signal = controller.signal;
    }
    
    return this.requestWithRetry<T>(endpoint, requestOptions, options?.retries);
  }

  async delete<T>(endpoint: string, options?: { retries?: number; timeout?: number }): Promise<T> {
    const requestOptions: RequestInit = {
      method: 'DELETE',
    };
    
    if (options?.timeout) {
      const controller = new AbortController();
      setTimeout(() => controller.abort(), options.timeout);
      requestOptions.signal = controller.signal;
    }
    
    return this.requestWithRetry<T>(endpoint, requestOptions, options?.retries);
  }
}

// Create HTTP client instance
const httpClient = new HttpClient(API_BASE_URL);

// API Client with typed methods
export class ApiClient {
  // Authentication endpoints
  static async login(credentials: LoginCredentials): Promise<LoginResponse> {
    console.log('ApiClient: Making login request to /api/auth/login');
    const response = await httpClient.post<LoginResponse>('/api/auth/login', credentials);
    console.log('ApiClient: Login response received:', response);
    
    // Check if login was successful
    if (!response.success) {
      console.error('ApiClient: Login failed:', response.message);
      throw new Error(response.message || 'Login failed');
    }
    
    // Store tokens after successful login
    if (response.tokens && response.expires_at) {
      console.log('ApiClient: Storing tokens');
      TokenManager.setTokens(response.tokens.access, response.tokens.refresh, response.expires_at);
      
      // Verify tokens were stored correctly
      const storedToken = TokenManager.getAccessToken();
      console.log('ApiClient: Token verification - stored token exists:', !!storedToken);
      
      // Small delay to ensure cookies are set before redirect
      await new Promise(resolve => setTimeout(resolve, 100));
    } else {
      console.warn('ApiClient: No tokens received in response');
    }
    
    return response;
  }

  static async validateSession(): Promise<AuthUser> {
    return httpClient.get<AuthUser>('/api/auth/me');
  }

  static async logout(): Promise<void> {
    try {
      await httpClient.post('/api/auth/logout');
    } finally {
      TokenManager.clearTokens();
    }
  }

  // Chat endpoints
  static async sendQuestion(question: string, conversationId?: string, userId?: string): Promise<ChatResponse> {
    const payload: any = {
      question,
      conversation_id: conversationId,
    };
    
    // Add user_id if provided (for HTTP fallback)
    if (userId) {
      payload.user_id = userId;
    }
    
    console.log('ApiClient.sendQuestion payload:', payload);
    return httpClient.post<ChatResponse>('/api/chat/question', payload);
  }

  static async submitFeedback(feedback: ChatFeedback): Promise<ChatFeedbackResponse> {
    return httpClient.post<ChatFeedbackResponse>('/api/chat/feedback', feedback);
  }

  static async getConversationHistory(
    userId: string,
    page: number = 1,
    limit: number = 20
  ): Promise<ConversationHistoryResponse> {
    return httpClient.get<ConversationHistoryResponse>(`/api/chat/history/${userId}`, {
      page,
      limit,
    });
  }

  static async getConversationDetail(conversationId: string): Promise<ConversationDetail> {
    return httpClient.get<ConversationDetail>(`/api/chat/conversations/${conversationId}`);
  }

  // ETL endpoints
  static async getETLJobs(
    userId: string,
    page: number = 1,
    limit: number = 20
  ): Promise<ETLJobsResponse> {
    return httpClient.get<ETLJobsResponse>(`/api/etl/users/${userId}/jobs`, {
      page,
      limit,
    });
  }

  static async getETLJobStatus(jobId: string): Promise<ETLJobStatusResponse> {
    return httpClient.get<ETLJobStatusResponse>(`/api/etl/jobs/${jobId}/status`);
  }

  static async retryETLJob(jobId: string): Promise<ETLJobResponse> {
    return httpClient.post<ETLJobResponse>(`/api/etl/jobs/${jobId}/retry`);
  }

  static async cancelETLJob(jobId: string): Promise<void> {
    return httpClient.post<void>(`/api/etl/jobs/${jobId}/cancel`);
  }

  static async triggerReprocessing(userId: string, force: boolean = false): Promise<ETLJobResponse> {
    return httpClient.post<ETLJobResponse>(`/api/etl/users/${userId}/reprocess`, {
      force,
    });
  }

  // User management endpoints
  static async getUserProfile(userId: string): Promise<UserProfileResponse> {
    return httpClient.get<UserProfileResponse>(`/api/users/${userId}/profile`);
  }

  static async getUserDocuments(
    userId: string,
    page: number = 1,
    limit: number = 20,
    docType?: string
  ): Promise<UserDocumentsResponse> {
    const params: Record<string, any> = { page, limit };
    if (docType) {
      params.doc_type = docType;
    }
    
    return httpClient.get<UserDocumentsResponse>(`/api/users/${userId}/documents`, params);
  }

  static async reprocessUserDocuments(userId: string, force: boolean = false): Promise<ETLJobResponse> {
    return httpClient.post<ETLJobResponse>(`/api/users/${userId}/reprocess`, {
      force,
    });
  }
}

// Export utilities
export { SecureTokenManager as TokenManager };
export default ApiClient;