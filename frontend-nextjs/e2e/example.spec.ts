import { expect, test } from '@playwright/test';

test.describe('E2E Navigation Flow', () => {
  test('landing page loads and navigates to login', async ({ page }) => {
    // 1. Visit Landing Page
    await page.goto('/');
    
    // Verify Header
    await expect(page.getByRole('heading', { name: 'Enterprise AI Agent' })).toBeVisible();
    
    // 2. Click Initialize Access (should go to payment or login depending on flow, 
    // but based on code it goes to /payment)
    const initLink = page.getByRole('link', { name: 'Initialize Access' });
    await expect(initLink).toBeVisible();
    await initLink.click();
    
    await expect(page).toHaveURL(/\/payment/);
  });

  test('login page rendering', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByText('Welcome Back')).toBeVisible();
    await expect(page.getByPlaceholderText('Email address')).toBeVisible();
  });

  // Note: Full auth flow and chat interaction requires mocking the backend 
  // or having a full environment running with valid credentials.
  // In a CI environment, you would mock the network requests or seed the database.
});
