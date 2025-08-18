// Chat API debug utilities to test direct backend communication

import { ChatResponse } from './types';
import { ApiClient, ApiErrorHandler } from './api';
import { SecureTokenManager } from './auth';
import { extractUserId } from './user-utils';

export interface ChatRequestDebug {
  payload: any;
  headers: Record<string, string>;
  url: string;
  method: string;
  timestamp: Date;
  userId?: string;
}

export interface ChatResponseDebug {
  success: boolean;
  data?: any;
  error?: string;
  status: number;
  duration: number;
  timestamp: Date;
  requestId: string;
}

export interface ApiTestResult {
  authValid: boolean;
  payloadValid: boolean;
  apiCallSuccess: boolean;
  responseValid: boolean;
  overallSuccess: boolean;
  errors: string[];
  debugLogs: ChatRequestDebug[];
  response?: ChatResponseDebug;
}

export class ChatApiDebugger {
  private static requestCounter = 0;

  /**
   * Logs detailed request information
   */
  static logRequest(request: ChatRequestDebug): void {
    console.group('📤 API REQUEST DEBUG');
    console.log('🕐 Timestamp:', request.timestamp.toISOString());
    console.log('🌐 URL:', request.url);
    console.log('📋 Method:', request.method);
    console.log('👤 User ID:', request.userId || 'Not provided');
    console.log('📦 Payload:', request.payload);
    console.log('🔑 Headers:', request.headers);
    console.groupEnd();
  }

  /**
   * Logs detailed response information
   */
  static logResponse(response: ChatResponseDebug): void {
    console.group('📥 API RESPONSE DEBUG');
    console.log('🕐 Timestamp:', response.timestamp.toISOString());
    console.log('✅ Success:', response.success ? '✅ YES' : '❌ NO');
    console.log('📊 Status:', response.status);
    console.log('⏱️ Duration:', `${response.duration}ms`);
    console.log('🆔 Request ID:', response.requestId);
    
    if (response.success && response.data) {
      console.log('📦 Response Data:', response.data);
    }
    
    if (!response.success && response.error) {
      console.log('❌ Error:', response.error);
    }
    
    console.groupEnd();
  }

  /**
   * Validates API request payload structure
   */
  static validatePayload(payload: any): string[] {
    const errors: string[] = [];
    
    if (!payload) {
      errors.push('Payload is null or undefined');
      return errors;
    }
    
    if (!payload.question || typeof payload.question !== 'string') {
      errors.push('Missing or invalid "question" field');
    }
    
    if (payload.question && payload.question.trim().length === 0) {
      errors.push('Question field is empty');
    }
    
    if (payload.conversation_id && typeof payload.conversation_id !== 'string') {
      errors.push('Invalid "conversation_id" field type');
    }
    
    if (payload.user_id && typeof payload.user_id !== 'string') {
      errors.push('Invalid "user_id" field type');
    }
    
    return errors;
  }

  /**
   * Tests direct API call to backend
   */
  static async testDirectApiCall(
    userId: string, 
    question: string = 'Test question for debugging',
    conversationId?: string
  ): Promise<ChatResponseDebug> {
    const requestId = `debug-${++this.requestCounter}-${Date.now()}`;
    const startTime = Date.now();
    
    console.log('🧪 Starting direct API test...');
    
    // Prepare request payload
    const payload = {
      question,
      conversation_id: conversationId,
      user_id: userId,
    };
    
    // Prepare headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    const accessToken = SecureTokenManager.getAccessToken();
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }
    
    const requestDebug: ChatRequestDebug = {
      payload,
      headers,
      url: '/api/chat/question',
      method: 'POST',
      timestamp: new Date(),
      userId,
    };
    
    this.logRequest(requestDebug);
    
    try {
      console.log('📞 Calling ApiClient.sendQuestion...');
      const response = await ApiClient.sendQuestion(question, conversationId, userId);
      
      const duration = Date.now() - startTime;
      const responseDebug: ChatResponseDebug = {
        success: true,
        data: response,
        status: 200,
        duration,
        timestamp: new Date(),
        requestId,
      };
      
      this.logResponse(responseDebug);
      console.log('✅ Direct API test completed successfully');
      
      return responseDebug;
    } catch (error: any) {
      const duration = Date.now() - startTime;
      let status = 500;
      let errorMessage = 'Unknown error';
      
      if (ApiErrorHandler.isApiError(error)) {
        status = error.status;
        errorMessage = error.message;
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      const responseDebug: ChatResponseDebug = {
        success: false,
        error: errorMessage,
        status,
        duration,
        timestamp: new Date(),
        requestId,
      };
      
      this.logResponse(responseDebug);
      console.log('❌ Direct API test failed');
      
      return responseDebug;
    }
  }

  /**
   * Runs comprehensive API integration test
   */
  static async runIntegrationTest(user: any): Promise<ApiTestResult> {
    console.group('🧪 CHAT API INTEGRATION TEST');
    
    const errors: string[] = [];
    const debugLogs: ChatRequestDebug[] = [];
    let response: ChatResponseDebug | undefined;
    
    // Step 1: Validate authentication
    console.log('1️⃣ Testing authentication state...');
    const userId = extractUserId(user);
    const authValid = !!userId && SecureTokenManager.isAuthenticated();
    
    if (!authValid) {
      errors.push('Authentication validation failed - no user ID or not authenticated');
    }
    
    console.log('Auth valid:', authValid ? '✅' : '❌');
    
    // Step 2: Validate payload structure
    console.log('2️⃣ Testing payload validation...');
    const testPayload = {
      question: 'Test question for integration test',
      conversation_id: undefined,
      user_id: userId,
    };
    
    const payloadErrors = this.validatePayload(testPayload);
    const payloadValid = payloadErrors.length === 0;
    
    if (!payloadValid) {
      errors.push(...payloadErrors);
    }
    
    console.log('Payload valid:', payloadValid ? '✅' : '❌');
    
    // Step 3: Test API call (only if auth and payload are valid)
    let apiCallSuccess = false;
    let responseValid = false;
    
    if (authValid && payloadValid) {
      console.log('3️⃣ Testing direct API call...');
      
      try {
        response = await this.testDirectApiCall(userId, testPayload.question);
        apiCallSuccess = response.success;
        
        // Step 4: Validate response structure
        if (apiCallSuccess && response.data) {
          console.log('4️⃣ Validating response structure...');
          responseValid = this.validateChatResponse(response.data);
        }
      } catch (error: any) {
        errors.push(`API call failed: ${error.message}`);
      }
    } else {
      errors.push('Skipping API call due to auth or payload validation failures');
    }
    
    console.log('API call success:', apiCallSuccess ? '✅' : '❌');
    console.log('Response valid:', responseValid ? '✅' : '❌');
    
    const overallSuccess = authValid && payloadValid && apiCallSuccess && responseValid;
    
    const result: ApiTestResult = {
      authValid,
      payloadValid,
      apiCallSuccess,
      responseValid,
      overallSuccess,
      errors,
      debugLogs,
      response,
    };
    
    console.log('🏁 Integration test result:', result);
    console.groupEnd();
    
    return result;
  }

  /**
   * Validates chat response structure
   */
  private static validateChatResponse(response: any): boolean {
    if (!response || typeof response !== 'object') {
      console.log('❌ Response is not an object');
      return false;
    }
    
    const requiredFields = ['conversation_id', 'response'];
    const missingFields = requiredFields.filter(field => !response[field]);
    
    if (missingFields.length > 0) {
      console.log('❌ Missing required fields:', missingFields);
      return false;
    }
    
    console.log('✅ Response structure is valid');
    return true;
  }

  /**
   * Creates a simple test function for manual testing
   */
  static createTestFunction(user: any): () => Promise<void> {
    return async () => {
      console.log('🚀 Running manual chat API test...');
      
      const userId = extractUserId(user);
      if (!userId) {
        console.error('❌ Cannot run test: No user ID available');
        return;
      }
      
      try {
        const result = await this.testDirectApiCall(
          userId,
          'Hello, this is a test message. Can you respond?'
        );
        
        if (result.success) {
          console.log('🎉 Manual test completed successfully!');
          console.log('Response:', result.data);
        } else {
          console.log('❌ Manual test failed:', result.error);
        }
      } catch (error) {
        console.error('❌ Manual test error:', error);
      }
    };
  }

  /**
   * Monitors API calls in real-time
   */
  static startApiMonitoring(): () => void {
    console.log('📡 Starting API monitoring...');
    
    // Store original fetch function
    const originalFetch = window.fetch;
    
    // Override fetch to monitor API calls
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString();
      
      // Only monitor chat API calls
      if (url.includes('/api/chat/')) {
        const startTime = Date.now();
        console.log('📡 Monitoring API call:', url);
        
        try {
          const response = await originalFetch(input, init);
          const duration = Date.now() - startTime;
          
          console.log('📡 API call completed:', {
            url,
            status: response.status,
            duration: `${duration}ms`,
            ok: response.ok,
          });
          
          return response;
        } catch (error) {
          const duration = Date.now() - startTime;
          console.log('📡 API call failed:', {
            url,
            error: error instanceof Error ? error.message : 'Unknown error',
            duration: `${duration}ms`,
          });
          throw error;
        }
      }
      
      return originalFetch(input, init);
    };
    
    // Return cleanup function
    return () => {
      console.log('📡 Stopping API monitoring...');
      window.fetch = originalFetch;
    };
  }
}

// Export convenience functions
export const testDirectApiCall = ChatApiDebugger.testDirectApiCall;
export const runIntegrationTest = ChatApiDebugger.runIntegrationTest;
export const validatePayload = ChatApiDebugger.validatePayload;
export const createTestFunction = ChatApiDebugger.createTestFunction;
export const startApiMonitoring = ChatApiDebugger.startApiMonitoring;