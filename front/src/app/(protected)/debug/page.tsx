'use client';

import React from 'react';
import { ChatDebugPanel } from '@/components/debug/chat-debug-panel';
import { ApiTestComponent } from '@/components/debug/api-test-component';

export default function DebugPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">Chat Integration Debug</h1>
          <p className="mt-2 text-gray-600">
            Debug utilities to identify and fix frontend-backend integration issues
          </p>
        </div>

        {/* API Test Component */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <ApiTestComponent />
          </div>
        </div>

        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-blue-900 mb-3">How to Use These Debug Tools</h2>
          <div className="space-y-3 text-blue-800">
            <div>
              <h3 className="font-medium">1. Check Authentication Status</h3>
              <p className="text-sm">The debug panel shows your current authentication state, including user ID and token validity.</p>
            </div>
            <div>
              <h3 className="font-medium">2. Run Direct API Test</h3>
              <p className="text-sm">Test the backend API directly without WebSocket complexity. This helps identify if the issue is in the API or WebSocket layer.</p>
            </div>
            <div>
              <h3 className="font-medium">3. Monitor API Calls</h3>
              <p className="text-sm">Use the floating debug panel (bottom right) to monitor all API calls in real-time.</p>
            </div>
            <div>
              <h3 className="font-medium">4. Check Browser Console</h3>
              <p className="text-sm">All debug tools log detailed information to the browser console. Open Developer Tools → Console to see the logs.</p>
            </div>
          </div>
        </div>

        {/* Common Issues */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-yellow-900 mb-3">Common Issues to Check</h2>
          <div className="grid md:grid-cols-2 gap-4 text-yellow-800">
            <div>
              <h3 className="font-medium">Authentication Issues</h3>
              <ul className="text-sm space-y-1 list-disc list-inside">
                <li>User ID missing or in wrong field (id vs user_id)</li>
                <li>Token expired or invalid</li>
                <li>Token not being sent in requests</li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium">API Issues</h3>
              <ul className="text-sm space-y-1 list-disc list-inside">
                <li>Incorrect payload structure</li>
                <li>Missing required fields</li>
                <li>Network connectivity problems</li>
                <li>Backend server errors</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Debug Commands */}
        <div className="bg-gray-100 border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Manual Debug Commands</h2>
          <p className="text-gray-600 mb-3">Run these commands in the browser console for additional debugging:</p>
          <div className="space-y-2 font-mono text-sm bg-gray-900 text-green-400 p-4 rounded">
            <div>// Log current auth state</div>
            <div>AuthDebugger.logAuthState(user)</div>
            <div></div>
            <div>// Test API directly</div>
            <div>ChatApiDebugger.testDirectApiCall(userId, "test message")</div>
            <div></div>
            <div>// Run integration test</div>
            <div>ChatApiDebugger.runIntegrationTest(user)</div>
            <div></div>
            <div>// Start API monitoring</div>
            <div>const cleanup = ChatApiDebugger.startApiMonitoring()</div>
          </div>
        </div>
      </div>

      {/* Floating Debug Panel */}
      <ChatDebugPanel enabled={true} />
    </div>
  );
}