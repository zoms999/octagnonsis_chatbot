# Design Document

## Overview

This design addresses the critical frontend-backend integration failure in the AI aptitude chatbot application. While the backend API functions correctly (verified via Swagger), the frontend chat interface fails to send messages or receive responses. The solution involves debugging and fixing the authentication flow, API integration, WebSocket/HTTP fallback mechanism, and user state management to restore full chat functionality.

## Architecture

### Problem Analysis
Based on code analysis, the integration failure likely stems from:
1. **Authentication State Issues**: User ID extraction problems in the frontend
2. **API Request Formation**: Incorrect payload structure or missing required fields
3. **WebSocket/HTTP Fallback Logic**: Complex fallback system may be preventing successful HTTP calls
4. **State Management**: React state updates may be interfering with message flow
5. **Token Management**: JWT token handling issues between frontend and backend

### Solution Architecture

#### Authentication Layer
- **User ID Resolution**: Ensure consistent user ID extraction across all components
- **Token Validation**: Verify JWT tokens are properly formatted and valid
- **Authentication State Sync**: Maintain consistent auth state between components

#### API Integration Layer
- **Request Payload Validation**: Ensure API requests match backend expectations exactly
- **Error Handling**: Implement comprehensive error logging and user feedback
- **Fallback Mechanism**: Simplify WebSocket/HTTP fallback to prioritize reliability

#### State Management Layer
- **Message Flow Control**: Prevent duplicate requests and state conflicts
- **Response Processing**: Ensure responses are properly processed and displayed
- **Debug Logging**: Add comprehensive logging throughout the message flow

## Components and Interfaces

### Authentication Debug Component

#### User State Validator (`lib/auth-debug.ts`)
```typescript
interface AuthDebugInfo {
  isAuthenticated: boolean;
  userId: string | null;
  userIdSource: 'id' | 'user_id' | 'missing';
  tokenExists: boolean;
  tokenValid: boolean;
  userObject: any;
}

class AuthDebugger {
  static validateAuthState(user: any): AuthDebugInfo;
  static logAuthState(user: any): void;
  static extractUserId(user: any): string | null;
}
```

### API Integration Components

#### Chat API Client (`lib/chat-api-debug.ts`)
```typescript
interface ChatRequestDebug {
  payload: any;
  headers: Record<string, string>;
  url: string;
  method: string;
  timestamp: Date;
}

interface ChatResponseDebug {
  success: boolean;
  data?: any;
  error?: string;
  status: number;
  duration: number;
}

class ChatApiDebugger {
  static logRequest(request: ChatRequestDebug): void;
  static logResponse(response: ChatResponseDebug): void;
  static validatePayload(payload: any): string[];
  static testDirectApiCall(userId: string, question: string): Promise<ChatResponseDebug>;
}
```

#### Simplified Chat Handler (`lib/simple-chat-handler.ts`)
```typescript
interface SimpleChatConfig {
  enableWebSocket: boolean;
  enableHttpFallback: boolean;
  debugMode: boolean;
}

class SimpleChatHandler {
  private config: SimpleChatConfig;
  
  constructor(config: SimpleChatConfig);
  
  async sendMessage(
    question: string,
    userId: string,
    conversationId?: string
  ): Promise<ChatResponse>;
  
  private async sendViaHttp(
    question: string,
    userId: string,
    conversationId?: string
  ): Promise<ChatResponse>;
  
  private async sendViaWebSocket(
    question: string,
    userId: string,
    conversationId?: string
  ): Promise<ChatResponse>;
}
```

### Debug Components

#### Chat Debug Panel (`components/debug/chat-debug-panel.tsx`)
```typescript
interface ChatDebugPanelProps {
  enabled: boolean;
  authState: AuthDebugInfo;
  lastRequest?: ChatRequestDebug;
  lastResponse?: ChatResponseDebug;
  onTestDirectCall: () => void;
  onClearLogs: () => void;
}

export function ChatDebugPanel(props: ChatDebugPanelProps): JSX.Element;
```

#### API Test Component (`components/debug/api-test-component.tsx`)
```typescript
interface ApiTestComponentProps {
  userId: string;
  onTestComplete: (result: ChatResponseDebug) => void;
}

export function ApiTestComponent(props: ApiTestComponentProps): JSX.Element;
```

## Data Models

### Debug Models
```typescript
interface ChatFlowDebug {
  step: 'auth' | 'payload' | 'request' | 'response' | 'state_update';
  timestamp: Date;
  success: boolean;
  data?: any;
  error?: string;
  duration?: number;
}

interface IntegrationTestResult {
  authValid: boolean;
  payloadValid: boolean;
  apiCallSuccess: boolean;
  responseValid: boolean;
  stateUpdateSuccess: boolean;
  overallSuccess: boolean;
  errors: string[];
  debugLogs: ChatFlowDebug[];
}
```

### Fixed Chat Models
```typescript
interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  conversation_id?: string;
  confidence_score?: number;
  processing_time?: number;
  retrieved_documents?: any[];
}

interface ChatState {
  messages: ChatMessage[];
  isProcessing: boolean;
  error: string | null;
  conversationId?: string;
}
```

## Error Handling

### Authentication Error Handling
1. **User ID Missing**: Clear error message with login redirect
2. **Token Invalid**: Automatic token refresh or re-authentication
3. **Auth State Inconsistent**: Force auth state validation and update

### API Error Handling
1. **Request Formation Errors**: Detailed logging of payload structure
2. **Network Errors**: Retry logic with exponential backoff
3. **Server Errors**: User-friendly messages with technical details in console
4. **Response Parsing Errors**: Fallback to raw response display

### State Management Error Handling
1. **Duplicate Requests**: Request deduplication and queuing
2. **State Update Conflicts**: Atomic state updates with conflict resolution
3. **Memory Leaks**: Proper cleanup of subscriptions and timers

## Testing Strategy

### Integration Tests
- **End-to-End Chat Flow**: Complete message send/receive cycle
- **Authentication Integration**: User login to chat message flow
- **API Compatibility**: Frontend requests match backend expectations
- **Error Recovery**: System behavior under various failure conditions

### Debug Tests
- **Auth State Validation**: Verify user ID extraction and token handling
- **API Request Formation**: Validate payload structure and headers
- **Response Processing**: Ensure responses are correctly parsed and displayed
- **Fallback Mechanisms**: Test WebSocket failure and HTTP fallback

### Manual Testing Procedures
1. **Direct API Test**: Use debug component to test API calls directly
2. **Authentication Flow**: Login and verify user state consistency
3. **Message Flow**: Send test messages and verify complete flow
4. **Error Scenarios**: Test various error conditions and recovery

## Implementation Approach

### Phase 1: Debug Infrastructure
1. Create comprehensive debug logging system
2. Implement auth state validator
3. Add API request/response logging
4. Create debug panel component

### Phase 2: Issue Identification
1. Use debug tools to identify exact failure point
2. Validate authentication state and user ID extraction
3. Test API payload formation and headers
4. Verify response processing and state updates

### Phase 3: Targeted Fixes
1. Fix identified authentication issues
2. Correct API integration problems
3. Simplify or fix WebSocket/HTTP fallback
4. Resolve state management conflicts

### Phase 4: Validation
1. Test complete chat flow end-to-end
2. Verify error handling and recovery
3. Ensure consistent behavior across scenarios
4. Remove debug code and finalize implementation