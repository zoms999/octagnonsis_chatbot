import { NextRequest, NextResponse } from 'next/server';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { middleware } from '../middleware';

// Mock fetch for API calls
global.fetch = vi.fn();

// Mock console.log for development logging
const mockConsoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});

// Helper to create NextRequest
function createRequest(url: string, options: { headers?: Record<string, string>; cookies?: Record<string, string> } = {}) {
  const request = new NextRequest(url);
  
  // Add headers
  if (options.headers) {
    Object.entries(options.headers).forEach(([key, value]) => {
      request.headers.set(key, value);
    });
  }
  
  // Add cookies
  if (options.cookies) {
    Object.entries(options.cookies).forEach(([key, value]) => {
      request.cookies.set(key, value);
    });
  }
  
  return request;
}

// Helper to create valid JWT token
function createValidJWT(expiresIn: number = 3600): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify({ 
    sub: 'user123', 
    exp: Math.floor(Date.now() / 1000) + expiresIn 
  }));
  const signature = 'mock-signature';
  return `${header}.${payload}.${signature}`;
}

// Helper to create expired JWT token
function createExpiredJWT(): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify({ 
    sub: 'user123', 
    exp: Math.floor(Date.now() / 1000) - 3600 // Expired 1 hour ago
  }));
  const signature = 'mock-signature';
  return `${header}.${payload}.${signature}`;
}

describe('Middleware Authentication and Route Protection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv('NODE_ENV', 'development');
  });

  afterEach(() => {
    vi.resetAllMocks();
    vi.unstubAllEnvs();
  });

  describe('Static files and API routes', () => {
    it('should skip middleware for Next.js static files', async () => {
      const request = createRequest('http://localhost:3000/_next/static/css/app.css');
      const response = await middleware(request);
      
      expect(response).toBeInstanceOf(NextResponse);
      expect(mockConsoleLog).not.toHaveBeenCalled();
    });

    it('should skip middleware for API routes', async () => {
      const request = createRequest('http://localhost:3000/api/auth/login');
      const response = await middleware(request);
      
      expect(response).toBeInstanceOf(NextResponse);
      expect(mockConsoleLog).not.toHaveBeenCalled();
    });
  });

  describe('Protected routes without authentication', () => {
    it('should redirect to login for unauthenticated user accessing chat', async () => {
      const request = createRequest('http://localhost:3000/chat');
      const response = await middleware(request);
      
      expect(response.status).toBe(307); // Redirect status
      expect(response.headers.get('location')).toBe('http://localhost:3000/login?returnTo=%2Fchat');
      expect(mockConsoleLog).toHaveBeenCalledWith('[Middleware] Processing request for /chat', '');
      expect(mockConsoleLog).toHaveBeenCalledWith('[Middleware] Redirecting unauthenticated user to login for /chat', '');
    });

    it('should clear invalid tokens when redirecting to login', async () => {
      const expiredToken = createExpiredJWT();
      const request = createRequest('http://localhost:3000/chat', {
        cookies: { access_token: expiredToken }
      });
      
      const response = await middleware(request);
      
      expect(response.status).toBe(307);
      // Check that cookies are cleared (set to empty values)
      expect(response.cookies.get('access_token')?.value).toBe('');
      expect(response.cookies.get('refresh_token')?.value).toBe('');
      expect(mockConsoleLog).toHaveBeenCalledWith('[Middleware] Invalid JWT token detected for /chat', '');
      expect(mockConsoleLog).toHaveBeenCalledWith('[Middleware] Cleared invalid tokens for /chat', '');
    });
  });

  describe('Protected routes with valid authentication', () => {
    it('should allow access to protected route with valid token and successful API validation', async () => {
      const validToken = createValidJWT();
      
      // Mock successful API validation
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        status: 200,
      } as Response);
      
      const request = createRequest('http://localhost:3000/chat', {
        cookies: { access_token: validToken }
      });
      
      const response = await middleware(request);
      
      expect(response).toBeInstanceOf(NextResponse);
      expect(response.status).toBe(200);
      expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/auth/me', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${validToken}`,
          'Content-Type': 'application/json',
        },
      });
      expect(mockConsoleLog).toHaveBeenCalledWith('[Middleware] Session validation successful for /api/auth/me', '');
      expect(mockConsoleLog).toHaveBeenCalledWith('[Middleware] Allowing access to protected route for /chat', '');
    });

    it('should redirect to login when API validation returns 401', async () => {
      const validToken = createValidJWT();
      
      // Mock 401 response from API
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 401,
      } as Response);
      
      const request = createRequest('http://localhost:3000/chat', {
        cookies: { access_token: validToken }
      });
      
      const response = await middleware(request);
      
      expect(response.status).toBe(307);
      expect(response.headers.get('location')).toBe('http://localhost:3000/login?returnTo=%2Fchat');
      // Check that cookies are cleared (set to empty values)
      expect(response.cookies.get('access_token')?.value).toBe('');
      expect(mockConsoleLog).toHaveBeenCalledWith('[Middleware] Session validation failed - 401 Unauthorized for /api/auth/me', '');
      expect(mockConsoleLog).toHaveBeenCalledWith('[Middleware] Cleared invalid tokens for /chat', '');
    });
  });

  describe('Authentication routes (login page)', () => {
    it('should allow access to login page for unauthenticated user', async () => {
      const request = createRequest('http://localhost:3000/login');
      const response = await middleware(request);
      
      expect(response).toBeInstanceOf(NextResponse);
      expect(response.status).toBe(200);
      expect(mockConsoleLog).toHaveBeenCalledWith('[Middleware] Allowing access to login page for /login', '');
    });

    it('should redirect authenticated user from login to chat', async () => {
      const validToken = createValidJWT();
      
      const request = createRequest('http://localhost:3000/login', {
        cookies: { access_token: validToken }
      });
      
      const response = await middleware(request);
      
      expect(response.status).toBe(307);
      expect(response.headers.get('location')).toBe('http://localhost:3000/chat');
      expect(mockConsoleLog).toHaveBeenCalledWith('[Middleware] Redirecting authenticated user from login for /login', { redirectUrl: '/chat' });
    });
  });

  describe('Token handling', () => {
    it('should get token from Authorization header', async () => {
      const validToken = createValidJWT();
      
      // Mock successful API validation
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        status: 200,
      } as Response);
      
      const request = createRequest('http://localhost:3000/chat', {
        headers: { authorization: `Bearer ${validToken}` }
      });
      
      const response = await middleware(request);
      
      expect(response.status).toBe(200);
      expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/auth/me', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${validToken}`,
          'Content-Type': 'application/json',
        },
      });
    });
  });
});