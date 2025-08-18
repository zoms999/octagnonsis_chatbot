import { test, expect } from '@playwright/test';
import { MockServer } from './utils/mock-server';
import { PageHelpers } from './utils/page-helpers';
import { testMessages } from './fixtures/test-data';

test.describe('Chat Functionality', () => {
  let mockServer: MockServer;
  let pageHelpers: PageHelpers;

  test.beforeEach(async ({ page }) => {
    mockServer = new MockServer(page);
    pageHelpers = new PageHelpers(page);
    
    await mockServer.setupAllMocks();
    await pageHelpers.login('personal');
  });

  test('should display chat interface correctly', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');

    // Check main chat elements
    await expect(page.locator('[data-testid="chat-container"]')).toBeVisible();
    await expect(page.locator('[data-testid="chat-messages"]')).toBeVisible();
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="send-button"]')).toBeVisible();
    await expect(page.locator('[data-testid="document-panel"]')).toBeVisible();
  });

  test('should establish WebSocket connection', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');

    // Wait for WebSocket connection
    await pageHelpers.waitForWebSocketConnection();

    // Check connection status indicator
    await expect(page.locator('[data-testid="connection-status"]')).toContainText('Connected');
  });

  test('should send message via WebSocket and receive response', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');
    await pageHelpers.waitForWebSocketConnection();

    const testQuestion = testMessages.questions[0];

    // Send message
    await pageHelpers.sendChatMessage(testQuestion);

    // Verify message appears in chat
    await expect(page.locator('[data-testid="chat-message"][data-sender="user"]').last())
      .toContainText(testQuestion);

    // Verify response appears
    await expect(page.locator('[data-testid="chat-message"][data-sender="assistant"]').last())
      .toBeVisible();

    // Check response metadata
    await expect(page.locator('[data-testid="confidence-score"]').last()).toBeVisible();
    await expect(page.locator('[data-testid="processing-time"]').last()).toBeVisible();
  });

  test('should show typing indicator during processing', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');
    await pageHelpers.waitForWebSocketConnection();

    // Send message
    await page.fill('[data-testid="chat-input"]', testMessages.questions[0]);
    await page.click('[data-testid="send-button"]');

    // Should show typing indicator
    await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible();

    // Wait for response
    await page.waitForSelector('[data-testid="typing-indicator"]', { state: 'hidden' });
  });

  test('should display retrieved documents in side panel', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');
    await pageHelpers.waitForWebSocketConnection();

    // Send message
    await pageHelpers.sendChatMessage(testMessages.questions[0]);

    // Check document panel
    await expect(page.locator('[data-testid="retrieved-documents"]')).toBeVisible();
    await expect(page.locator('[data-testid="document-item"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="relevance-score"]').first()).toBeVisible();
  });

  test('should fallback to HTTP when WebSocket fails', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');

    // Simulate WebSocket failure
    await page.evaluate(() => {
      // Force WebSocket to fail
      window.localStorage.setItem('websocket-status', 'failed');
    });

    // Send message (should use HTTP fallback)
    await pageHelpers.sendChatMessage(testMessages.questions[0]);

    // Should show fallback indicator
    await expect(page.locator('[data-testid="fallback-mode"]')).toBeVisible();

    // Response should still appear
    await expect(page.locator('[data-testid="chat-message"][data-sender="assistant"]').last())
      .toBeVisible();
  });

  test('should handle rate limiting gracefully', async ({ page }) => {
    // Mock rate limit response
    await mockServer.simulateRateLimit('**/api/chat/**');

    await pageHelpers.navigateTo('/chat');

    // Try to send message
    await page.fill('[data-testid="chat-input"]', testMessages.questions[0]);
    await page.click('[data-testid="send-button"]');

    // Should show rate limit message
    await expect(page.locator('[data-testid="rate-limit-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="rate-limit-countdown"]')).toBeVisible();

    // Input should be disabled
    await expect(page.locator('[data-testid="chat-input"]')).toBeDisabled();
  });

  test('should validate input and show empty state message', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');

    // Try to send empty message
    await page.click('[data-testid="send-button"]');

    // Should not send empty message
    const messageCount = await page.locator('[data-testid="chat-message"]').count();
    expect(messageCount).toBe(0);

    // Should show validation message
    await expect(page.locator('[data-testid="input-validation"]')).toBeVisible();
  });

  test('should show helpful message when user has no documents', async ({ page }) => {
    // Mock empty documents response
    await page.route('**/api/users/*/documents', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ documents: [], total: 0 }),
      });
    });

    await pageHelpers.navigateTo('/chat');

    // Should show no documents message
    await expect(page.locator('[data-testid="no-documents-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="upload-documents-link"]')).toBeVisible();
  });

  test('should submit feedback for chat responses', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');
    await pageHelpers.waitForWebSocketConnection();

    // Send message and get response
    await pageHelpers.sendChatMessage(testMessages.questions[0]);

    // Click feedback button
    await page.click('[data-testid="feedback-helpful"]');

    // Should show feedback confirmation
    await pageHelpers.waitForToast('success');
    await expect(page.locator('[data-testid="toast-success"]'))
      .toContainText('Feedback submitted');
  });

  test('should handle WebSocket reconnection', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');
    await pageHelpers.waitForWebSocketConnection();

    // Simulate connection loss
    await page.evaluate(() => {
      // Trigger WebSocket close event
      const event = new Event('close');
      window.dispatchEvent(event);
    });

    // Should show reconnecting status
    await expect(page.locator('[data-testid="connection-status"]'))
      .toContainText('Reconnecting');

    // Should eventually reconnect
    await pageHelpers.waitForWebSocketConnection();
    await expect(page.locator('[data-testid="connection-status"]'))
      .toContainText('Connected');
  });

  test('should maintain conversation context', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');
    await pageHelpers.waitForWebSocketConnection();

    // Send first message
    await pageHelpers.sendChatMessage(testMessages.questions[0]);

    // Send follow-up message
    await pageHelpers.sendChatMessage('Can you elaborate on that?');

    // Both messages should be visible
    const messageCount = await page.locator('[data-testid="chat-message"]').count();
    expect(messageCount).toBeGreaterThanOrEqual(4); // 2 user + 2 assistant messages
  });

  test('should handle network errors gracefully', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');

    // Simulate network error
    await mockServer.simulateNetworkError('**/api/chat/**');

    // Try to send message
    await page.fill('[data-testid="chat-input"]', testMessages.questions[0]);
    await page.click('[data-testid="send-button"]');

    // Should show error message
    await expect(page.locator('[data-testid="network-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
  });

  test('should work on mobile devices', async ({ page }) => {
    await pageHelpers.setMobileViewport();
    await pageHelpers.navigateTo('/chat');

    // Check mobile layout
    await expect(page.locator('[data-testid="chat-container"]')).toBeVisible();
    
    // Document panel should be collapsible on mobile
    const documentPanel = page.locator('[data-testid="document-panel"]');
    if (await documentPanel.isVisible()) {
      await expect(page.locator('[data-testid="panel-toggle"]')).toBeVisible();
    }

    // Chat input should be accessible
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
  });

  test('should handle long messages and scrolling', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');
    await pageHelpers.waitForWebSocketConnection();

    // Send multiple messages to test scrolling
    for (let i = 0; i < 5; i++) {
      await pageHelpers.sendChatMessage(`Test message ${i + 1}: ${testMessages.questions[i % testMessages.questions.length]}`);
      await page.waitForTimeout(1000); // Wait between messages
    }

    // Should auto-scroll to latest message
    const lastMessage = page.locator('[data-testid="chat-message"]').last();
    await expect(lastMessage).toBeInViewport();
  });

  test('should display confidence scores and processing metrics', async ({ page }) => {
    await pageHelpers.navigateTo('/chat');
    await pageHelpers.waitForWebSocketConnection();

    await pageHelpers.sendChatMessage(testMessages.questions[0]);

    // Check metrics display
    await expect(page.locator('[data-testid="confidence-score"]').last()).toBeVisible();
    await expect(page.locator('[data-testid="processing-time"]').last()).toBeVisible();
    await expect(page.locator('[data-testid="document-count"]').last()).toBeVisible();

    // Verify confidence score format
    const confidenceText = await page.locator('[data-testid="confidence-score"]').last().textContent();
    expect(confidenceText).toMatch(/\d+%/); // Should show percentage
  });
});