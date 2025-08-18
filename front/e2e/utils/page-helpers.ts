import { Page, expect } from '@playwright/test';
import { testUsers } from '../fixtures/test-data';

/**
 * Page helper utilities for common E2E test actions
 */
export class PageHelpers {
  constructor(private page: Page) {}

  /**
   * Navigate to a specific page and wait for it to load
   */
  async navigateTo(path: string) {
    await this.page.goto(path);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Perform login with specified user type
   */
  async login(userType: 'personal' | 'organization' | 'admin' = 'personal') {
    const user = testUsers[userType];
    
    await this.navigateTo('/login');
    
    // Select login type
    await this.page.click(`[data-testid="login-type-${user.loginType}"]`);
    
    // Fill credentials
    await this.page.fill('[data-testid="username-input"]', user.username);
    await this.page.fill('[data-testid="password-input"]', user.password);
    
    // Fill session code for organization login
    if (user.loginType === 'organization' && 'sessionCode' in user) {
      await this.page.fill('[data-testid="session-code-input"]', user.sessionCode);
    }
    
    // Submit login
    await this.page.click('[data-testid="login-submit"]');
    
    // Wait for redirect to chat page
    await this.page.waitForURL('/chat');
    await expect(this.page.locator('[data-testid="user-menu"]')).toBeVisible();
  }

  /**
   * Logout from the application
   */
  async logout() {
    await this.page.click('[data-testid="user-menu"]');
    await this.page.click('[data-testid="logout-button"]');
    await this.page.waitForURL('/login');
  }

  /**
   * Send a chat message and wait for response
   */
  async sendChatMessage(message: string) {
    await this.page.fill('[data-testid="chat-input"]', message);
    await this.page.click('[data-testid="send-button"]');
    
    // Wait for message to appear in chat
    await expect(this.page.locator('[data-testid="chat-message"]').last()).toContainText(message);
    
    // Wait for response
    await this.page.waitForSelector('[data-testid="typing-indicator"]', { state: 'visible' });
    await this.page.waitForSelector('[data-testid="typing-indicator"]', { state: 'hidden' });
    
    // Verify response appears
    await expect(this.page.locator('[data-testid="chat-message"][data-sender="assistant"]').last()).toBeVisible();
  }

  /**
   * Wait for WebSocket connection to be established
   */
  async waitForWebSocketConnection() {
    await this.page.waitForFunction(() => {
      return window.localStorage.getItem('websocket-status') === 'connected';
    });
  }

  /**
   * Check if element is visible with timeout
   */
  async isVisible(selector: string, timeout = 5000): Promise<boolean> {
    try {
      await this.page.waitForSelector(selector, { state: 'visible', timeout });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Wait for loading to complete
   */
  async waitForLoading() {
    await this.page.waitForSelector('[data-testid="loading-spinner"]', { state: 'hidden' });
  }

  /**
   * Check for error messages
   */
  async checkForErrors() {
    const errorElements = await this.page.locator('[data-testid="error-message"]').count();
    return errorElements > 0;
  }

  /**
   * Take screenshot for debugging
   */
  async takeScreenshot(name: string) {
    await this.page.screenshot({ 
      path: `e2e/screenshots/${name}-${Date.now()}.png`,
      fullPage: true 
    });
  }

  /**
   * Simulate mobile viewport
   */
  async setMobileViewport() {
    await this.page.setViewportSize({ width: 375, height: 667 });
  }

  /**
   * Simulate desktop viewport
   */
  async setDesktopViewport() {
    await this.page.setViewportSize({ width: 1280, height: 720 });
  }

  /**
   * Check accessibility violations
   */
  async checkAccessibility() {
    // Basic accessibility checks
    const missingAltText = await this.page.locator('img:not([alt])').count();
    const missingLabels = await this.page.locator('input:not([aria-label]):not([aria-labelledby])').count();
    
    return {
      missingAltText,
      missingLabels,
      hasViolations: missingAltText > 0 || missingLabels > 0
    };
  }

  /**
   * Simulate keyboard navigation
   */
  async navigateWithKeyboard() {
    await this.page.keyboard.press('Tab');
    await this.page.keyboard.press('Tab');
    await this.page.keyboard.press('Enter');
  }

  /**
   * Wait for API call to complete
   */
  async waitForApiCall(endpoint: string) {
    await this.page.waitForResponse(response => 
      response.url().includes(endpoint) && response.status() === 200
    );
  }

  /**
   * Fill form with validation
   */
  async fillFormField(selector: string, value: string, shouldValidate = true) {
    await this.page.fill(selector, value);
    
    if (shouldValidate) {
      // Trigger validation by blurring the field
      await this.page.blur(selector);
      
      // Check for validation errors
      const errorSelector = `${selector}-error`;
      const hasError = await this.isVisible(errorSelector, 1000);
      
      return !hasError;
    }
    
    return true;
  }

  /**
   * Wait for toast notification
   */
  async waitForToast(type: 'success' | 'error' | 'info' = 'success') {
    await this.page.waitForSelector(`[data-testid="toast-${type}"]`, { state: 'visible' });
  }

  /**
   * Close modal or overlay
   */
  async closeModal() {
    const closeButton = this.page.locator('[data-testid="modal-close"]');
    if (await closeButton.isVisible()) {
      await closeButton.click();
    } else {
      await this.page.keyboard.press('Escape');
    }
  }

  /**
   * Scroll to element
   */
  async scrollToElement(selector: string) {
    await this.page.locator(selector).scrollIntoViewIfNeeded();
  }

  /**
   * Check responsive design
   */
  async checkResponsiveLayout() {
    const viewports = [
      { width: 375, height: 667, name: 'mobile' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 1280, height: 720, name: 'desktop' },
    ];

    const results = [];

    for (const viewport of viewports) {
      await this.page.setViewportSize({ width: viewport.width, height: viewport.height });
      await this.page.waitForTimeout(500); // Allow layout to adjust
      
      const isNavigationVisible = await this.isVisible('[data-testid="navigation"]');
      const isSidebarVisible = await this.isVisible('[data-testid="sidebar"]');
      
      results.push({
        viewport: viewport.name,
        navigationVisible: isNavigationVisible,
        sidebarVisible: isSidebarVisible,
      });
    }

    return results;
  }
}