# Chat Integration Debug Utilities

This directory contains debug utilities to help identify and fix frontend-backend integration issues in the chat system.

## Files Created

### Core Debug Libraries
- `auth-debug.ts` - Authentication state debugging utilities
- `chat-api-debug.ts` - API call debugging and direct testing utilities  
- `debug-utils.ts` - Quick debug functions and global utilities

### Debug Components
- `components/debug/chat-debug-panel.tsx` - Floating debug panel for real-time monitoring
- `components/debug/api-test-component.tsx` - Direct API testing component
- `components/debug/index.ts` - Export file for debug components

### Debug Pages
- `app/(protected)/debug/page.tsx` - Dedicated debug page with all tools

### Tests
- `lib/__tests__/debug-utils.test.ts` - Unit tests for debug utilities

## How to Use

### 1. Access Debug Page
Navigate to `/debug` in your application to access the comprehensive debug interface.

### 2. Floating Debug Panel
The floating debug panel appears in the bottom-right corner when `debugMode` is enabled on the ChatContainer component.

### 3. Console Commands
In development mode, the following functions are automatically exposed to the global scope:

```javascript
// Quick comprehensive debug
quickDebug()

// Test API directly
quickApiTest()

// Authentication debug
authDebug()

// Full integration test
runIntegrationTest()
```

### 4. Manual Testing
```javascript
// Test authentication state
import { AuthDebugger } from '@/lib/auth-debug';
AuthDebugger.logAuthState(user);

// Test API call directly
import { ChatApiDebugger } from '@/lib/chat-api-debug';
await ChatApiDebugger.testDirectApiCall(userId, "test message");

// Run comprehensive integration test
await ChatApiDebugger.runIntegrationTest(user);
```

## Debug Information Provided

### Authentication Debug
- User ID extraction and validation
- Token existence and validity
- Token expiration status
- Authentication state consistency
- Common authentication issues identification

### API Debug
- Request payload validation
- Direct API call testing
- Response structure validation
- Error classification and handling
- Network connectivity testing

### Integration Debug
- End-to-end flow testing
- Component integration validation
- State management verification
- Error recovery testing

## Common Issues Detected

1. **User ID Missing**: No user ID available in user object
2. **Wrong ID Field**: User ID in legacy `user_id` field instead of `id`
3. **Token Issues**: Expired, invalid, or missing authentication tokens
4. **Payload Errors**: Incorrect API request structure
5. **Network Problems**: Connectivity or server issues
6. **State Conflicts**: React state management problems

## Integration with Chat Container

The debug utilities are automatically integrated into the ChatContainer component:

- Enhanced logging of authentication state changes
- Auto-debug on errors in development mode
- Global debug function exposure
- Optional floating debug panel

## Environment Configuration

Debug features are automatically enabled in development mode (`NODE_ENV === 'development'`) and can be manually enabled by setting the `debugMode` prop on components.

## Console Output

All debug utilities provide comprehensive console output with:
- Grouped logging for easy reading
- Color-coded status indicators
- Detailed error analysis
- Step-by-step execution logs
- Suggested troubleshooting steps

## Testing

Run the debug utility tests with:
```bash
npm test -- debug-utils.test.ts --run
```

The tests verify:
- User ID extraction logic
- Authentication state validation
- API payload validation
- Error handling
- Console logging functionality