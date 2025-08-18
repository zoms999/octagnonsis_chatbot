'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/providers/auth-provider';
import { AuthDebugger, AuthDebugInfo } from '@/lib/auth-debug';
import { 
  ChatApiDebugger, 
  ChatResponseDebug, 
  ApiTestResult,
  createTestFunction,
  startApiMonitoring 
} from '@/lib/chat-api-debug';
import { cn } from '@/lib/utils';
import { extractUserId } from '@/lib/user-utils';

interface ChatDebugPanelProps {
  enabled?: boolean;
  className?: string;
}

export function ChatDebugPanel({ enabled = true, className }: ChatDebugPanelProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const [isExpanded, setIsExpanded] = useState(false);
  const [authDebugInfo, setAuthDebugInfo] = useState<AuthDebugInfo | null>(null);
  const [lastTestResult, setLastTestResult] = useState<ChatResponseDebug | null>(null);
  const [integrationTestResult, setIntegrationTestResult] = useState<ApiTestResult | null>(null);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [monitoringCleanup, setMonitoringCleanup] = useState<(() => void) | null>(null);

  // Update auth debug info when user changes
  useEffect(() => {
    if (enabled) {
      const debugInfo = AuthDebugger.validateAuthState(user);
      setAuthDebugInfo(debugInfo);
    }
  }, [user, isAuthenticated, isLoading, enabled]);

  // Don't render if not enabled
  if (!enabled) {
    return null;
  }

  const handleLogAuthState = () => {
    AuthDebugger.logAuthState(user);
  };

  const handleRunDirectTest = async () => {
    const userId = extractUserId(user);
    if (!userId) {
      console.error('Cannot run test: No user ID available');
      return;
    }

    try {
      const result = await ChatApiDebugger.testDirectApiCall(
        userId,
        'Debug test: Can you respond to this message?'
      );
      setLastTestResult(result);
    } catch (error) {
      console.error('Direct test failed:', error);
    }
  };

  const handleRunIntegrationTest = async () => {
    try {
      const result = await ChatApiDebugger.runIntegrationTest(user);
      setIntegrationTestResult(result);
    } catch (error) {
      console.error('Integration test failed:', error);
    }
  };

  const handleToggleMonitoring = () => {
    if (isMonitoring) {
      // Stop monitoring
      if (monitoringCleanup) {
        monitoringCleanup();
        setMonitoringCleanup(null);
      }
      setIsMonitoring(false);
    } else {
      // Start monitoring
      const cleanup = startApiMonitoring();
      setMonitoringCleanup(() => cleanup);
      setIsMonitoring(true);
    }
  };

  const handleRunDebugTest = () => {
    AuthDebugger.runDebugTest(user);
  };

  const handleCreateManualTest = () => {
    const testFn = createTestFunction(user);
    // Expose test function to global scope for manual execution
    (window as any).runChatTest = testFn;
    console.log('🧪 Manual test function created! Run "runChatTest()" in console to execute.');
  };

  return (
    <div className={cn(
      'fixed bottom-4 right-4 z-50 bg-white border border-gray-300 rounded-lg shadow-lg',
      'max-w-md',
      className
    )}>
      {/* Header */}
      <div 
        className="flex items-center justify-between p-3 bg-gray-50 border-b cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          <span className="text-sm font-medium text-gray-700">Chat Debug</span>
        </div>
        <div className="flex items-center gap-2">
          {authDebugInfo && (
            <div className={cn(
              'w-2 h-2 rounded-full',
              authDebugInfo.isAuthenticated ? 'bg-green-500' : 'bg-red-500'
            )} />
          )}
          <svg 
            className={cn('w-4 h-4 transition-transform', isExpanded && 'rotate-180')}
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-3 space-y-3 max-h-96 overflow-y-auto">
          {/* Auth Status */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700">Authentication Status</h4>
            {authDebugInfo && (
              <div className="text-xs space-y-1">
                <div className="flex justify-between">
                  <span>Authenticated:</span>
                  <span className={authDebugInfo.isAuthenticated ? 'text-green-600' : 'text-red-600'}>
                    {authDebugInfo.isAuthenticated ? '✅' : '❌'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>User ID:</span>
                  <span className={authDebugInfo.userId ? 'text-green-600' : 'text-red-600'}>
                    {authDebugInfo.userId ? '✅' : '❌'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Token Valid:</span>
                  <span className={authDebugInfo.tokenValid ? 'text-green-600' : 'text-red-600'}>
                    {authDebugInfo.tokenValid ? '✅' : '❌'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>ID Source:</span>
                  <span className="text-gray-600">{authDebugInfo.userIdSource}</span>
                </div>
              </div>
            )}
          </div>

          {/* Test Results */}
          {lastTestResult && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700">Last API Test</h4>
              <div className="text-xs space-y-1">
                <div className="flex justify-between">
                  <span>Success:</span>
                  <span className={lastTestResult.success ? 'text-green-600' : 'text-red-600'}>
                    {lastTestResult.success ? '✅' : '❌'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Status:</span>
                  <span>{lastTestResult.status}</span>
                </div>
                <div className="flex justify-between">
                  <span>Duration:</span>
                  <span>{lastTestResult.duration}ms</span>
                </div>
                {lastTestResult.error && (
                  <div className="text-red-600 text-xs mt-1">
                    Error: {lastTestResult.error}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Integration Test Results */}
          {integrationTestResult && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700">Integration Test</h4>
              <div className="text-xs space-y-1">
                <div className="flex justify-between">
                  <span>Overall:</span>
                  <span className={integrationTestResult.overallSuccess ? 'text-green-600' : 'text-red-600'}>
                    {integrationTestResult.overallSuccess ? '✅' : '❌'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Auth:</span>
                  <span className={integrationTestResult.authValid ? 'text-green-600' : 'text-red-600'}>
                    {integrationTestResult.authValid ? '✅' : '❌'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Payload:</span>
                  <span className={integrationTestResult.payloadValid ? 'text-green-600' : 'text-red-600'}>
                    {integrationTestResult.payloadValid ? '✅' : '❌'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>API Call:</span>
                  <span className={integrationTestResult.apiCallSuccess ? 'text-green-600' : 'text-red-600'}>
                    {integrationTestResult.apiCallSuccess ? '✅' : '❌'}
                  </span>
                </div>
                {integrationTestResult.errors.length > 0 && (
                  <div className="text-red-600 text-xs mt-1">
                    Errors: {integrationTestResult.errors.length}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-2">
            <button
              onClick={handleLogAuthState}
              className="w-full px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
            >
              Log Auth State
            </button>
            
            <button
              onClick={handleRunDirectTest}
              className="w-full px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
              disabled={!authDebugInfo?.userId}
            >
              Test Direct API Call
            </button>
            
            <button
              onClick={handleRunIntegrationTest}
              className="w-full px-3 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
            >
              Run Integration Test
            </button>
            
            <button
              onClick={handleToggleMonitoring}
              className={cn(
                'w-full px-3 py-1 text-xs rounded',
                isMonitoring 
                  ? 'bg-red-100 text-red-700 hover:bg-red-200' 
                  : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
              )}
            >
              {isMonitoring ? 'Stop Monitoring' : 'Start API Monitoring'}
            </button>
            
            <button
              onClick={handleRunDebugTest}
              className="w-full px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
            >
              Run Debug Test Suite
            </button>
            
            <button
              onClick={handleCreateManualTest}
              className="w-full px-3 py-1 text-xs bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200"
            >
              Create Manual Test Function
            </button>
          </div>

          {/* Instructions */}
          <div className="text-xs text-gray-500 border-t pt-2">
            <p>Open browser console to see detailed debug logs.</p>
            {isMonitoring && (
              <p className="text-yellow-600 mt-1">🔍 API monitoring active</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}