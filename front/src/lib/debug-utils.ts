// Quick debug utilities for chat integration issues

import { AuthDebugger } from './auth-debug';
import { ChatApiDebugger } from './chat-api-debug';
import { extractUserId, getUserIdDebugInfo } from './user-utils';

/**
 * Quick debug function that can be called from anywhere
 * Logs comprehensive debug information to console
 */
export function quickDebug(user: any): void {
  console.group('🚀 QUICK DEBUG - Chat Integration');
  
  // Log auth state
  AuthDebugger.logAuthState(user);
  
  // Log user object details
  console.group('👤 User Object Analysis');
  console.log('Raw user object:', user);
  console.log('Type of user:', typeof user);
  console.log('User is null/undefined:', user == null);
  console.log('User has id property:', 'id' in (user || {}));
  console.log('User has user_id property:', 'user_id' in (user || {}));
  console.log('Object keys:', user ? Object.keys(user) : 'N/A');
  console.groupEnd();
  
  // Check token state
  console.group('🎫 Token Analysis');
  const token = localStorage.getItem('access_token');
  console.log('Token exists in localStorage:', !!token);
  if (token) {
    console.log('Token preview:', token.substring(0, 50) + '...');
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      console.log('Token payload:', payload);
      console.log('Token expires:', new Date(payload.exp * 1000));
      console.log('Token expired:', Date.now() > payload.exp * 1000);
    } catch (e) {
      console.log('Failed to decode token:', e);
    }
  }
  console.groupEnd();
  
  // Check environment
  console.group('🌍 Environment Check');
  console.log('API Base URL:', process.env.NEXT_PUBLIC_API_BASE);
  console.log('WebSocket Base URL:', process.env.NEXT_PUBLIC_WS_BASE);
  console.log('Current URL:', window.location.href);
  console.log('User Agent:', navigator.userAgent);
  console.groupEnd();
  
  console.groupEnd();
}

/**
 * Quick API test function
 */
export async function quickApiTest(user: any): Promise<void> {
  console.log('🧪 Running quick API test...');
  
  const userId = AuthDebugger.extractUserId(user);
  if (!userId) {
    console.error('❌ Cannot run API test: No user ID');
    return;
  }
  
  try {
    const result = await ChatApiDebugger.testDirectApiCall(
      userId,
      'Quick test: Hello, can you respond?'
    );
    
    if (result.success) {
      console.log('✅ Quick API test passed!');
    } else {
      console.log('❌ Quick API test failed:', result.error);
    }
  } catch (error) {
    console.error('❌ Quick API test error:', error);
  }
}

/**
 * Expose debug functions to global scope for easy console access
 */
export function exposeDebugFunctions(user: any): void {
  (window as any).quickDebug = () => quickDebug(user);
  (window as any).quickApiTest = () => quickApiTest(user);
  (window as any).authDebug = () => AuthDebugger.logAuthState(user);
  (window as any).runIntegrationTest = () => ChatApiDebugger.runIntegrationTest(user);
  
  console.log('🔧 Debug functions exposed to global scope:');
  console.log('  - quickDebug() - Comprehensive debug info');
  console.log('  - quickApiTest() - Quick API test');
  console.log('  - authDebug() - Authentication debug');
  console.log('  - runIntegrationTest() - Full integration test');
}

/**
 * Auto-debug function that runs when there are issues
 */
export function autoDebugOnError(user: any, error: any): void {
  console.group('🚨 AUTO DEBUG - Error Detected');
  console.log('Error that triggered debug:', error);
  
  quickDebug(user);
  
  // Suggest next steps
  console.group('💡 Suggested Next Steps');
  console.log('1. Check if user is properly authenticated');
  console.log('2. Verify token is valid and not expired');
  console.log('3. Test API directly with quickApiTest()');
  console.log('4. Check network connectivity');
  console.log('5. Verify backend server is running');
  console.groupEnd();
  
  console.groupEnd();
}