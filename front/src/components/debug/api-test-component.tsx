'use client';

import React, { useState } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { ChatApiDebugger, ChatResponseDebug } from '@/lib/chat-api-debug';
import { AuthDebugger } from '@/lib/auth-debug';
import { cn } from '@/lib/utils';

interface ApiTestComponentProps {
  className?: string;
}

export function ApiTestComponent({ className }: ApiTestComponentProps) {
  const { user } = useAuth();
  const [testQuestion, setTestQuestion] = useState('Hello, can you help me understand my aptitude test results?');
  const [isLoading, setIsLoading] = useState(false);
  const [testResult, setTestResult] = useState<ChatResponseDebug | null>(null);
  const [showRawResponse, setShowRawResponse] = useState(false);

  const handleRunTest = async () => {
    // First, log the current auth state
    console.log('🧪 API Test Component: Starting test...');
    AuthDebugger.logAuthState(user);

    const userId = AuthDebugger.extractUserId(user);
    if (!userId) {
      console.error('❌ Cannot run test: No user ID available');
      setTestResult({
        success: false,
        error: 'No user ID available',
        status: 0,
        duration: 0,
        timestamp: new Date(),
        requestId: 'no-user-id',
      });
      return;
    }

    setIsLoading(true);
    setTestResult(null);

    try {
      console.log('🚀 Running direct API test with userId:', userId);
      const result = await ChatApiDebugger.testDirectApiCall(userId, testQuestion.trim());
      setTestResult(result);
      
      if (result.success) {
        console.log('🎉 API test completed successfully!');
      } else {
        console.log('❌ API test failed:', result.error);
      }
    } catch (error: any) {
      console.error('❌ API test error:', error);
      setTestResult({
        success: false,
        error: error.message || 'Unknown error occurred',
        status: 0,
        duration: 0,
        timestamp: new Date(),
        requestId: 'error',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearResults = () => {
    setTestResult(null);
  };

  const userId = AuthDebugger.extractUserId(user);
  const authDebugInfo = AuthDebugger.validateAuthState(user);

  return (
    <div className={cn('p-4 border border-gray-200 rounded-lg bg-white', className)}>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Direct API Test</h3>
          <div className="flex items-center gap-2">
            <div className={cn(
              'w-2 h-2 rounded-full',
              authDebugInfo.isAuthenticated ? 'bg-green-500' : 'bg-red-500'
            )} />
            <span className="text-sm text-gray-600">
              {authDebugInfo.isAuthenticated ? 'Authenticated' : 'Not Authenticated'}
            </span>
          </div>
        </div>

        {/* Auth Status */}
        <div className="p-3 bg-gray-50 rounded-md">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Authentication Status</h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex justify-between">
              <span>User ID:</span>
              <span className={userId ? 'text-green-600' : 'text-red-600'}>
                {userId ? `${userId.substring(0, 8)}...` : 'Missing'}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Token:</span>
              <span className={authDebugInfo.tokenValid ? 'text-green-600' : 'text-red-600'}>
                {authDebugInfo.tokenValid ? 'Valid' : 'Invalid'}
              </span>
            </div>
            <div className="flex justify-between">
              <span>ID Source:</span>
              <span className="text-gray-600">{authDebugInfo.userIdSource}</span>
            </div>
            <div className="flex justify-between">
              <span>Expired:</span>
              <span className={authDebugInfo.tokenExpired ? 'text-red-600' : 'text-green-600'}>
                {authDebugInfo.tokenExpired ? 'Yes' : 'No'}
              </span>
            </div>
          </div>
        </div>

        {/* Test Input */}
        <div className="space-y-2">
          <label htmlFor="test-question" className="block text-sm font-medium text-gray-700">
            Test Question
          </label>
          <textarea
            id="test-question"
            value={testQuestion}
            onChange={(e) => setTestQuestion(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            rows={3}
            placeholder="Enter a test question to send to the API..."
          />
        </div>

        {/* Test Button */}
        <div className="flex gap-2">
          <button
            onClick={handleRunTest}
            disabled={isLoading || !userId || !testQuestion.trim()}
            className={cn(
              'flex-1 px-4 py-2 rounded-md font-medium',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              isLoading 
                ? 'bg-gray-100 text-gray-600' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            )}
          >
            {isLoading ? 'Testing...' : 'Run Direct API Test'}
          </button>
          
          {testResult && (
            <button
              onClick={handleClearResults}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Clear
            </button>
          )}
        </div>

        {/* Test Results */}
        {testResult && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-700">Test Results</h4>
              <button
                onClick={() => setShowRawResponse(!showRawResponse)}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                {showRawResponse ? 'Hide Raw' : 'Show Raw'}
              </button>
            </div>
            
            {/* Result Summary */}
            <div className={cn(
              'p-3 rounded-md',
              testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
            )}>
              <div className="flex items-center gap-2 mb-2">
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  testResult.success ? 'bg-green-500' : 'bg-red-500'
                )} />
                <span className={cn(
                  'font-medium',
                  testResult.success ? 'text-green-800' : 'text-red-800'
                )}>
                  {testResult.success ? 'Success' : 'Failed'}
                </span>
              </div>
              
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex justify-between">
                  <span>Status:</span>
                  <span>{testResult.status}</span>
                </div>
                <div className="flex justify-between">
                  <span>Duration:</span>
                  <span>{testResult.duration}ms</span>
                </div>
                <div className="flex justify-between">
                  <span>Timestamp:</span>
                  <span>{testResult.timestamp.toLocaleTimeString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Request ID:</span>
                  <span className="font-mono text-xs">{testResult.requestId}</span>
                </div>
              </div>
              
              {testResult.error && (
                <div className="mt-2 p-2 bg-red-100 rounded text-sm text-red-700">
                  <strong>Error:</strong> {testResult.error}
                </div>
              )}
            </div>

            {/* Response Data */}
            {testResult.success && testResult.data && (
              <div className="space-y-2">
                <h5 className="text-sm font-medium text-gray-700">Response Data</h5>
                <div className="p-3 bg-gray-50 rounded-md">
                  <div className="space-y-2 text-sm">
                    <div>
                      <strong>Conversation ID:</strong> {testResult.data.conversation_id}
                    </div>
                    <div>
                      <strong>Response:</strong>
                      <div className="mt-1 p-2 bg-white rounded border text-gray-700">
                        {testResult.data.response?.substring(0, 200)}
                        {testResult.data.response?.length > 200 && '...'}
                      </div>
                    </div>
                    {testResult.data.confidence_score && (
                      <div>
                        <strong>Confidence:</strong> {(testResult.data.confidence_score * 100).toFixed(1)}%
                      </div>
                    )}
                    {testResult.data.processing_time && (
                      <div>
                        <strong>Processing Time:</strong> {testResult.data.processing_time}ms
                      </div>
                    )}
                    {testResult.data.retrieved_documents && (
                      <div>
                        <strong>Retrieved Documents:</strong> {testResult.data.retrieved_documents.length}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Raw Response */}
            {showRawResponse && (
              <div className="space-y-2">
                <h5 className="text-sm font-medium text-gray-700">Raw Response</h5>
                <pre className="p-3 bg-gray-900 text-green-400 rounded-md text-xs overflow-x-auto">
                  {JSON.stringify(testResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Instructions */}
        <div className="text-xs text-gray-500 border-t pt-3">
          <p><strong>Instructions:</strong></p>
          <ul className="mt-1 space-y-1 list-disc list-inside">
            <li>This component tests the API directly, bypassing WebSocket logic</li>
            <li>Check the browser console for detailed debug logs</li>
            <li>Ensure you're authenticated before running the test</li>
            <li>The test will validate auth state, payload, and API response</li>
          </ul>
        </div>
      </div>
    </div>
  );
}