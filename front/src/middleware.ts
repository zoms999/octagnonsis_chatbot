import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

// Define protected and public routes
const protectedRoutes = ['/chat', '/history', '/profile', '/documents', '/etl'];
const authRoutes = ['/login'];
const publicRoutes = ['/'];

// Helper function to check if a path matches any of the route patterns
function matchesRoute(pathname: string, routes: string[]): boolean {
  return routes.some(route => {
    if (route === pathname) return true;
    if (route.endsWith('*')) {
      const baseRoute = route.slice(0, -1);
      return pathname.startsWith(baseRoute);
    }
    return pathname.startsWith(route);
  });
}

// Enhanced logging for middleware actions
function logMiddlewareAction(action: string, pathname: string, details?: any): void {
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Middleware] ${action} for ${pathname}`, details || '');
  }
}

// Helper function to get token from request
function getTokenFromRequest(request: NextRequest): string | null {
  // Try to get token from Authorization header
  const authHeader = request.headers.get('authorization');
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return authHeader.substring(7);
  }

  // Try to get token from cookies
  const tokenFromCookie = request.cookies.get('access_token')?.value;
  if (tokenFromCookie) {
    return tokenFromCookie;
  }

  return null;
}

// Helper function to validate JWT token (basic validation)
function isValidToken(token: string): boolean {
  try {
    // Basic JWT structure validation
    const parts = token.split('.');
    if (parts.length !== 3) return false;

    // Decode payload to check expiration
    const payload = JSON.parse(atob(parts[1]));
    const now = Math.floor(Date.now() / 1000);
    
    // Check if token is expired
    if (payload.exp && payload.exp < now) {
      return false;
    }

    return true;
  } catch {
    return false;
  }
}

// Helper function to validate session with backend API
async function validateSessionWithAPI(token: string): Promise<{ isValid: boolean; shouldLogout: boolean }> {
  try {
    // Create AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (response.ok) {
      logMiddlewareAction('Session validation successful', '/api/auth/me');
      return { isValid: true, shouldLogout: false };
    }

    // Handle 401 responses - token is invalid/expired
    if (response.status === 401) {
      logMiddlewareAction('Session validation failed - 401 Unauthorized', '/api/auth/me');
      return { isValid: false, shouldLogout: true };
    }

    // Handle other error responses
    logMiddlewareAction('Session validation failed', '/api/auth/me', { status: response.status });
    return { isValid: false, shouldLogout: false };
  } catch (error) {
    logMiddlewareAction('Session validation network error', '/api/auth/me', error);
    // On network errors, don't force logout but consider token invalid
    return { isValid: false, shouldLogout: false };
  }
}

// Helper function to clear authentication cookies
function clearAuthCookies(response: NextResponse): void {
  // Set cookies to empty values with immediate expiration
  response.cookies.set('access_token', '', { 
    expires: new Date(0),
    path: '/',
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax'
  });
  response.cookies.set('refresh_token', '', { 
    expires: new Date(0),
    path: '/',
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax'
  });
  response.cookies.set('token_expires', '', { 
    expires: new Date(0),
    path: '/',
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax'
  });
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Skip middleware for static files and API routes
  if (
    pathname.startsWith('/_next/') ||
    pathname.startsWith('/api/') ||
    pathname.includes('.') // Static files (images, css, js, etc.)
  ) {
    return NextResponse.next();
  }

  logMiddlewareAction('Processing request', pathname);

  // Get token from request
  const token = getTokenFromRequest(request);
  let isAuthenticated = false;
  let shouldClearTokens = false;

  // Validate token if present
  if (token) {
    // First do basic JWT validation
    const isValidJWT = isValidToken(token);
    
    if (isValidJWT) {
      // For protected routes, try to validate with backend API but be more forgiving
      if (matchesRoute(pathname, protectedRoutes)) {
        try {
          const { isValid, shouldLogout } = await validateSessionWithAPI(token);
          isAuthenticated = isValid;
          shouldClearTokens = shouldLogout;
        } catch (error) {
          // If API validation fails due to network issues, trust the JWT for now
          logMiddlewareAction('API validation failed, trusting JWT', pathname, error);
          isAuthenticated = true;
          shouldClearTokens = false;
        }
      } else {
        // For non-protected routes, basic JWT validation is sufficient
        isAuthenticated = true;
      }
    } else {
      logMiddlewareAction('Invalid JWT token detected', pathname);
      shouldClearTokens = true;
    }
  }

  // Handle protected routes
  if (matchesRoute(pathname, protectedRoutes)) {
    if (!isAuthenticated) {
      logMiddlewareAction('Redirecting unauthenticated user to login', pathname);
      
      // Redirect to login with return URL
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('returnTo', pathname);
      
      const response = NextResponse.redirect(loginUrl);
      
      // Clear any invalid tokens
      if (token || shouldClearTokens) {
        clearAuthCookies(response);
        logMiddlewareAction('Cleared invalid tokens', pathname);
      }
      
      return response;
    }
    
    logMiddlewareAction('Allowing access to protected route', pathname);
    return NextResponse.next();
  }

  // Handle auth routes (login page)
  if (matchesRoute(pathname, authRoutes)) {
    if (isAuthenticated) {
      // User is already authenticated, redirect to appropriate page
      const returnTo = request.nextUrl.searchParams.get('returnTo');
      let redirectUrl = '/chat'; // default redirect
      
      // Validate returnTo parameter
      if (returnTo) {
        try {
          const returnPath = new URL(returnTo, request.url).pathname;
          if (matchesRoute(returnPath, protectedRoutes)) {
            redirectUrl = returnPath;
          }
        } catch {
          // Invalid returnTo URL, use default
          logMiddlewareAction('Invalid returnTo parameter, using default', pathname, { returnTo });
        }
      }
      
      logMiddlewareAction('Redirecting authenticated user from login', pathname, { redirectUrl });
      return NextResponse.redirect(new URL(redirectUrl, request.url));
    }
    
    // Clear invalid tokens even on login page
    if (shouldClearTokens) {
      const response = NextResponse.next();
      clearAuthCookies(response);
      logMiddlewareAction('Cleared invalid tokens on login page', pathname);
      return response;
    }
    
    logMiddlewareAction('Allowing access to login page', pathname);
    return NextResponse.next();
  }

  // Handle public routes and root
  if (matchesRoute(pathname, publicRoutes) || pathname === '/') {
    if (isAuthenticated && pathname === '/') {
      logMiddlewareAction('Redirecting authenticated user from root to chat', pathname);
      return NextResponse.redirect(new URL('/chat', request.url));
    }
    
    // Clear invalid tokens on public routes too
    if (shouldClearTokens) {
      const response = NextResponse.next();
      clearAuthCookies(response);
      logMiddlewareAction('Cleared invalid tokens on public route', pathname);
      return response;
    }
    
    logMiddlewareAction('Allowing access to public route', pathname);
    return NextResponse.next();
  }

  // Default: allow access but clear invalid tokens
  if (shouldClearTokens) {
    const response = NextResponse.next();
    clearAuthCookies(response);
    logMiddlewareAction('Cleared invalid tokens on default route', pathname);
    return response;
  }

  logMiddlewareAction('Allowing access to default route', pathname);
  return NextResponse.next();
}

// Configure which routes the middleware should run on
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.).*)',
  ],
};