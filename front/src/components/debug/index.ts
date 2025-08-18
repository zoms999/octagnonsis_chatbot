// Debug components for chat integration troubleshooting

export { ChatDebugPanel } from './chat-debug-panel';
export { ApiTestComponent } from './api-test-component';

// Re-export debug utilities for convenience
export { 
  AuthDebugger, 
  logAuthState, 
  validateAuthState, 
  extractUserId 
} from '@/lib/auth-debug';

export { 
  ChatApiDebugger, 
  testDirectApiCall, 
  runIntegrationTest, 
  validatePayload, 
  createTestFunction, 
  startApiMonitoring 
} from '@/lib/chat-api-debug';