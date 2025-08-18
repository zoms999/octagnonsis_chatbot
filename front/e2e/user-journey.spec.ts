import { test, expect } from '@playwright/test';
import { MockServer } from './utils/mock-server';
import { PageHelpers } from './utils/page-helpers';
import { testUsers, testMessages } from './fixtures/test-data';

test.describe('Complete User Journey', () => {
  let mockServer: MockServer;
  let pageHelpers: PageHelpers;

  test.beforeEach(async ({ page }) => {
    mockServer = new MockServer(page);
    pageHelpers = new PageHelpers(page);
    
    await mockServer.setupAllMocks();
  });

  test('Complete flow: Login → Chat → Send Message → Logout', async ({ page }) => {
    // Step 1: Start from login page
    await pageHelpers.navigateTo('/login');
    
    // Verify we're on login page
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
    
    // Step 2: Perform login
    const user = testUsers.personal;
    await page.click('[data-testid="login-type-personal"]');
    await page.fill('[data-testid="username-input"]', user.username);
    await page.fill('[data-testid="password-input"]', user.password);
    await page.click('[data-testid="login-submit"]');
    
    // Step 3: Verify redirect to chat page
    await page.waitForURL('/chat');
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    await expect(page.locator('[data-testid="chat-container"]')).toBeVisible();
    
    // Step 4: Wait for WebSocket connection
    await pageHelpers.waitForWebSocketConnection();
    await expect(page.locator('[data-testid="connection-status"]')).toContainText('Connected');
    
    // Step 5: Send a chat message
    const testQuestion = testMessages.questions[0];
    await page.fill('[data-testid="chat-input"]', testQuestion);
    await page.click('[data-testid="send-button"]');
    
    // Step 6: Verify message appears in chat
    await expect(page.locator('[data-testid="chat-message"][data-sender="user"]').last())
      .toContainText(testQuestion);
    
    // Step 7: Wait for and verify AI response
    await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible();
    await page.waitForSelector('[data-testid="typing-indicator"]', { state: 'hidden' });
    await expect(page.locator('[data-testid="chat-message"][data-sender="assistant"]').last())
      .toBeVisible();
    
    // Step 8: Verify response metadata
    await expect(page.locator('[data-testid="confidence-score"]').last()).toBeVisible();
    await expect(page.locator('[data-testid="processing-time"]').last()).toBeVisible();
    
    // Step 9: Verify document panel shows retrieved documents
    await expect(page.locator('[data-testid="retrieved-documents"]')).toBeVisible();
    await expect(page.locator('[data-testid="document-item"]').first()).toBeVisible();
    
    // Step 10: Perform logout
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="logout-button"]');
    
    // Step 11: Verify redirect to login page
    await page.waitForURL('/login');
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
    
    // Step 12: Verify user is actually logged out (no auth state)
    await expect(page.locator('[data-testid="user-menu"]')).not.toBeVisible();
  });

  test('Organization user journey with session code', async ({ page }) => {
    // Step 1: Navigate to login
    await pageHelpers.navigateTo('/login');
    
    // Step 2: Select organization login type
    await page.click('[data-testid="login-type-organization"]');
    await expect(page.locator('[data-testid="session-code-input"]')).toBeVisible();
    
    // Step 3: Fill organization credentials
    const user = testUsers.organization;
    await page.fill('[data-testid="username-input"]', user.username);
    await page.fill('[data-testid="password-input"]', user.password);
    await page.fill('[data-testid="session-code-input"]', user.sessionCode);
    
    // Step 4: Login and verify chat access
    await page.click('[data-testid="login-submit"]');
    await page.waitForURL('/chat');
    
    // Step 5: Send message and verify functionality
    await pageHelpers.waitForWebSocketConnection();
    await pageHelpers.sendChatMessage(testMessages.questions[1]);
    
    // Step 6: Logout
    await pageHelpers.logout();
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
  });

  test('Multiple conversation flow', async ({ page }) => {
    // Login
    await pageHelpers.login('personal');
    
    // Send multiple messages in sequence
    const questions = testMessages.questions.slice(0, 3);
    
    for (let i = 0; i < questions.length; i++) {
      await pageHelpers.sendChatMessage(questions[i]);
      
      // Verify each message and response pair
      const userMessages = page.locator('[data-testid="chat-message"][data-sender="user"]');
      const assistantMessages = page.locator('[data-testid="chat-message"][data-sender="assistant"]');
      
      await expect(userMessages).toHaveCount(i + 1);
      await expect(assistantMessages).toHaveCount(i + 1);
    }
    
    // Verify conversation context is maintained
    const totalMessages = await page.locator('[data-testid="chat-message"]').count();
    expect(totalMessages).toBe(6); // 3 user + 3 assistant messages
    
    // Logout
    await pageHelpers.logout();
  });

  test('Error handling during user journey', async ({ page }) => {
    // Login successfully
    await pageHelpers.login('personal');
    
    // Simulate WebSocket failure
    await page.evaluate(() => {
      window.localStorage.setItem('websocket-status', 'failed');
    });
    
    // Send message (should fallback to HTTP)
    await page.fill('[data-testid="chat-input"]', testMessages.questions[0]);
    await page.click('[data-testid="send-button"]');
    
    // Verify fallback mode is active
    await expect(page.locator('[data-testid="fallback-mode"]')).toBeVisible();
    
    // Verify message still works
    await expect(page.locator('[data-testid="chat-message"][data-sender="assistant"]').last())
      .toBeVisible();
    
    // Logout should still work
    await pageHelpers.logout();
  });

  test('Session persistence across page refresh', async ({ page }) => {
    // Login
    await pageHelpers.login('personal');
    
    // Send a message
    await pageHelpers.sendChatMessage(testMessages.questions[0]);
    
    // Refresh the page
    await page.reload();
    
    // Verify still authenticated and on chat page
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    await expect(page.locator('[data-testid="chat-container"]')).toBeVisible();
    
    // Verify previous conversation is still visible
    await expect(page.locator('[data-testid="chat-message"]')).toHaveCount(2); // user + assistant
    
    // Send another message to verify functionality
    await pageHelpers.waitForWebSocketConnection();
    await pageHelpers.sendChatMessage(testMessages.questions[1]);
    
    // Logout
    await pageHelpers.logout();
  });

  test('Rate limiting handling during conversation', async ({ page }) => {
    // Login
    await pageHelpers.login('personal');
    
    // Send first message successfully
    await pageHelpers.sendChatMessage(testMessages.questions[0]);
    
    // Mock rate limit for next request
    await mockServer.simulateRateLimit('**/api/chat/**');
    
    // Try to send another message
    await page.fill('[data-testid="chat-input"]', testMessages.questions[1]);
    await page.click('[data-testid="send-button"]');
    
    // Verify rate limit handling
    await expect(page.locator('[data-testid="rate-limit-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="chat-input"]')).toBeDisabled();
    
    // Wait for rate limit to clear (simulate)
    await page.evaluate(() => {
      setTimeout(() => {
        window.localStorage.removeItem('rate-limit-until');
      }, 2000);
    });
    
    await page.waitForTimeout(2500);
    
    // Verify input is re-enabled
    await expect(page.locator('[data-testid="chat-input"]')).toBeEnabled();
    
    // Logout
    await pageHelpers.logout();
  });

  test('Mobile responsive user journey', async ({ page }) => {
    // Set mobile viewport
    await pageHelpers.setMobileViewport();
    
    // Login on mobile
    await pageHelpers.login('personal');
    
    // Verify mobile layout
    await expect(page.locator('[data-testid="chat-container"]')).toBeVisible();
    
    // Check if document panel is collapsible on mobile
    const documentPanel = page.locator('[data-testid="document-panel"]');
    if (await documentPanel.isVisible()) {
      await expect(page.locator('[data-testid="panel-toggle"]')).toBeVisible();
    }
    
    // Send message on mobile
    await pageHelpers.sendChatMessage(testMessages.questions[0]);
    
    // Verify mobile chat functionality
    await expect(page.locator('[data-testid="chat-message"]')).toHaveCount(2);
    
    // Logout on mobile
    await pageHelpers.logout();
  });

  test('Accessibility during user journey', async ({ page }) => {
    // Login
    await pageHelpers.login('personal');
    
    // Check accessibility on chat page
    const accessibilityResults = await pageHelpers.checkAccessibility();
    expect(accessibilityResults.hasViolations).toBe(false);
    
    // Test keyboard navigation
    await page.keyboard.press('Tab'); // Should focus chat input
    await expect(page.locator('[data-testid="chat-input"]')).toBeFocused();
    
    await page.keyboard.press('Tab'); // Should focus send button
    await expect(page.locator('[data-testid="send-button"]')).toBeFocused();
    
    // Send message via keyboard
    await page.focus('[data-testid="chat-input"]');
    await page.keyboard.type(testMessages.questions[0]);
    await page.keyboard.press('Enter');
    
    // Verify message was sent
    await expect(page.locator('[data-testid="chat-message"][data-sender="user"]').last())
      .toContainText(testMessages.questions[0]);
    
    // Logout
    await pageHelpers.logout();
  });

  test('Network error recovery during journey', async ({ page }) => {
    // Login
    await pageHelpers.login('personal');
    
    // Simulate network error
    await mockServer.simulateNetworkError('**/api/chat/**');
    
    // Try to send message
    await page.fill('[data-testid="chat-input"]', testMessages.questions[0]);
    await page.click('[data-testid="send-button"]');
    
    // Verify error handling
    await expect(page.locator('[data-testid="network-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
    
    // Restore network and retry
    await mockServer.restoreNetwork();
    await page.click('[data-testid="retry-button"]');
    
    // Verify message goes through
    await expect(page.locator('[data-testid="chat-message"][data-sender="assistant"]').last())
      .toBeVisible();
    
    // Logout should still work
    await pageHelpers.logout();
  });

  test('Complete journey with feedback submission', async ({ page }) => {
    // Login and send message
    await pageHelpers.login('personal');
    await pageHelpers.sendChatMessage(testMessages.questions[0]);
    
    // Submit positive feedback
    await page.click('[data-testid="feedback-helpful"]');
    await pageHelpers.waitForToast('success');
    
    // Send another message
    await pageHelpers.sendChatMessage(testMessages.questions[1]);
    
    // Submit detailed feedback
    await page.click('[data-testid="feedback-detailed"]');
    await page.fill('[data-testid="feedback-comment"]', 'Very helpful response!');
    await page.click('[data-testid="feedback-submit"]');
    await pageHelpers.waitForToast('success');
    
    // Logout
    await pageHelpers.logout();
  });
});