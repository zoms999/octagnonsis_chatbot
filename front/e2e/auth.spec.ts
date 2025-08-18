import { test, expect } from '@playwright/test';
import { MockServer } from './utils/mock-server';
import { PageHelpers } from './utils/page-helpers';
import { testUsers } from './fixtures/test-data';

test.describe('Authentication Flow', () => {
  let mockServer: MockServer;
  let pageHelpers: PageHelpers;

  test.beforeEach(async ({ page }) => {
    mockServer = new MockServer(page);
    pageHelpers = new PageHelpers(page);
    
    await mockServer.mockAuthEndpoints();
  });

  test('should display login form with correct elements', async ({ page }) => {
    await pageHelpers.navigateTo('/login');

    // Check login form elements
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-type-personal"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-type-organization"]')).toBeVisible();
    await expect(page.locator('[data-testid="username-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="password-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-submit"]')).toBeVisible();
  });

  test('should show session code field for organization login', async ({ page }) => {
    await pageHelpers.navigateTo('/login');

    // Initially session code should be hidden
    await expect(page.locator('[data-testid="session-code-input"]')).not.toBeVisible();

    // Select organization login type
    await page.click('[data-testid="login-type-organization"]');

    // Session code field should now be visible
    await expect(page.locator('[data-testid="session-code-input"]')).toBeVisible();
  });

  test('should successfully login with personal credentials', async ({ page }) => {
    await pageHelpers.navigateTo('/login');

    const user = testUsers.personal;

    // Fill login form
    await page.click('[data-testid="login-type-personal"]');
    await page.fill('[data-testid="username-input"]', user.username);
    await page.fill('[data-testid="password-input"]', user.password);

    // Submit login
    await page.click('[data-testid="login-submit"]');

    // Should redirect to chat page
    await page.waitForURL('/chat');
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('should successfully login with organization credentials', async ({ page }) => {
    await pageHelpers.navigateTo('/login');

    const user = testUsers.organization;

    // Fill login form
    await page.click('[data-testid="login-type-organization"]');
    await page.fill('[data-testid="username-input"]', user.username);
    await page.fill('[data-testid="password-input"]', user.password);
    await page.fill('[data-testid="session-code-input"]', user.sessionCode);

    // Submit login
    await page.click('[data-testid="login-submit"]');

    // Should redirect to chat page
    await page.waitForURL('/chat');
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    await pageHelpers.navigateTo('/login');

    // Try to submit empty form
    await page.click('[data-testid="login-submit"]');

    // Should show validation errors
    await expect(page.locator('[data-testid="username-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="password-error"]')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    // Mock failed login
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Invalid credentials' }),
      });
    });

    await pageHelpers.navigateTo('/login');

    // Fill with invalid credentials
    await page.fill('[data-testid="username-input"]', 'invalid_user');
    await page.fill('[data-testid="password-input"]', 'invalid_password');
    await page.click('[data-testid="login-submit"]');

    // Should show error message
    await expect(page.locator('[data-testid="login-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-error"]')).toContainText('Invalid credentials');
  });

  test('should handle session validation on app start', async ({ page }) => {
    // Mock valid session
    await mockServer.mockAuthEndpoints();

    // Set existing token in localStorage
    await page.addInitScript(() => {
      localStorage.setItem('auth-token', 'valid-token');
    });

    await pageHelpers.navigateTo('/');

    // Should automatically redirect to chat if valid session
    await page.waitForURL('/chat');
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('should logout and redirect to login page', async ({ page }) => {
    // Login first
    await pageHelpers.login('personal');

    // Logout
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="logout-button"]');

    // Should redirect to login page
    await page.waitForURL('/login');
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
  });

  test('should handle automatic logout on 401 response', async ({ page }) => {
    // Login first
    await pageHelpers.login('personal');

    // Mock 401 response for protected endpoint
    await page.route('**/api/users/*/profile', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Unauthorized' }),
      });
    });

    // Navigate to profile page (triggers API call)
    await pageHelpers.navigateTo('/profile');

    // Should automatically logout and redirect to login
    await page.waitForURL('/login');
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
  });

  test('should protect routes requiring authentication', async ({ page }) => {
    // Try to access protected route without authentication
    await pageHelpers.navigateTo('/chat');

    // Should redirect to login page
    await page.waitForURL('/login');
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
  });

  test('should maintain authentication state across page refreshes', async ({ page }) => {
    // Login first
    await pageHelpers.login('personal');

    // Refresh the page
    await page.reload();

    // Should still be authenticated
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    expect(page.url()).toContain('/chat');
  });

  test('should handle network errors during login', async ({ page }) => {
    // Mock network error
    await page.route('**/api/auth/login', async (route) => {
      await route.abort('failed');
    });

    await pageHelpers.navigateTo('/login');

    // Fill and submit form
    await page.fill('[data-testid="username-input"]', testUsers.personal.username);
    await page.fill('[data-testid="password-input"]', testUsers.personal.password);
    await page.click('[data-testid="login-submit"]');

    // Should show network error message
    await expect(page.locator('[data-testid="network-error"]')).toBeVisible();
  });
});