import { describe, it, expect, beforeEach, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { middleware } from '../middleware';

// Mock fetch for API calls
global.fetch = vi.fn();

describe('Middleware Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv('NODE_ENV', 'development');
  });

  it('should handle complete authentication flow', async () => {
    // Test 1: Unauthenticated user accessing protected route
    const request1 = new NextRequest('http://localhost:3000/chat');
    const response1 = await middleware(request1);
    
    expect(response1.status).toBe(307);
    expect(response1.headers.get('location')).toBe('http://localhost:3000/login?returnTo=%2Fchat');

    // Test 2: User with valid token accessing protected route
    const validToken = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })) + '.' +
                      btoa(JSON.stringify({ sub: 'user123', exp: Math.floor(Date.now() / 1000) + 3600 })) + 
                      '.signature';

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
    } as Response);

    const request2 = new NextRequest('http://localhost:3000/chat');
    request2.cookies.set('access_token', validToken);
    const response2 = await middleware(request2);
    
    expect(response2.status).toBe(200);
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/auth/me', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${validToken}`,
        'Content-Type': 'application/json',
      },
    });

    // Test 3: Authenticated user accessing login page should redirect
    const request3 = new NextRequest('http://localhost:3000/login');
    request3.cookies.set('access_token', validToken);
    const response3 = await middleware(request3);
    
    expect(response3.status).toBe(307);
    expect(response3.headers.get('location')).toBe('http://localhost:3000/chat');
  });

  it('should handle 401 responses and clear tokens', async () => {
    const validToken = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })) + '.' +
                      btoa(JSON.stringify({ sub: 'user123', exp: Math.floor(Date.now() / 1000) + 3600 })) + 
                      '.signature';

    // Mock 401 response from API
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 401,
    } as Response);

    const request = new NextRequest('http://localhost:3000/chat');
    request.cookies.set('access_token', validToken);
    const response = await middleware(request);
    
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('http://localhost:3000/login?returnTo=%2Fchat');
    expect(response.cookies.get('access_token')?.value).toBe('');
  });

  it('should validate returnTo parameter security', async () => {
    const validToken = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })) + '.' +
                      btoa(JSON.stringify({ sub: 'user123', exp: Math.floor(Date.now() / 1000) + 3600 })) + 
                      '.signature';

    // Test with malicious returnTo URL
    const request = new NextRequest('http://localhost:3000/login?returnTo=http://evil.com/steal');
    request.cookies.set('access_token', validToken);
    const response = await middleware(request);
    
    expect(response.status).toBe(307);
    // Should redirect to default chat page, not the malicious URL
    expect(response.headers.get('location')).toBe('http://localhost:3000/chat');
  });
});