import { test, expect } from '@playwright/test';

test.describe('CandidateX Login Page', () => {
  test('renders with CandidateX styling and header context without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/login');
    await expect(page).toHaveTitle(/Sign In \| CandidateX/);

    // Verify PlatformHeader surface is active
    const header = page.locator('header.platform-header');
    await expect(header).toBeVisible();

    // Verify brand
    await expect(header.locator('.platform-brand__wordmark')).toHaveText('CandidateX');

    // Verify Narrative content
    await expect(page.locator('#narrative-heading')).toContainText('Candidate');
    await expect(page.locator('#narrative-heading')).toContainText('with receipts.');

    // Verify Invariants are visible
    await expect(page.getByText('Closed-world candidate manifest')).toBeVisible();
    await expect(page.getByText('Candidate code is never executed')).toBeVisible();
    await expect(page.getByText('Unknown stays unknown')).toBeVisible();

    // Verify Auth Card
    await expect(page.getByRole('heading', { name: 'Sign in to workspace' })).toBeVisible();
    await expect(page.getByRole('tab', { name: /Interviewer/ })).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByRole('tab', { name: /Candidate/ })).toHaveAttribute('aria-selected', 'false');

    expect(errors).toEqual([]);
  });

  test('quick demo button fills credentials and submits to workspace', async ({ page }) => {
    await page.goto('/login');

    const emailInput = page.locator('#login-email');
    const passwordInput = page.locator('#login-password');

    // Click quick demo
    await page.getByRole('button', { name: 'Yorayriniwnl' }).click();

    await expect(emailInput).toHaveValue('Yorayriniwnl');
    await expect(passwordInput).toHaveValue('Yorayriniwnl');

    // Toggle password reveal
    await page.getByRole('button', { name: 'Show password' }).click();
    await expect(passwordInput).toHaveAttribute('type', 'text');
    await page.getByRole('button', { name: 'Hide password' }).click();
    await expect(passwordInput).toHaveAttribute('type', 'password');

    // Submit form
    await page.getByRole('button', { name: 'Sign in to workspace' }).click();

    // Should redirect to workspace
    await expect(page).toHaveURL(/\/workspace$/, { timeout: 15000 });
  });

  test('shows validation errors when submitting invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.locator('#login-email').fill('unknown_user');
    await page.locator('#login-password').fill('secret');

    await page.getByRole('button', { name: 'Sign in to workspace' }).click();

    await expect(page.getByTestId('login-error')).toContainText('Invalid credentials');
  });

  test('role switcher toggles context and candidate role redirects to live evidence', async ({ page }) => {
    await page.goto('/login');

    await page.getByRole('tab', { name: /Candidate/ }).click();
    await expect(page.getByRole('heading', { name: 'Review your evidence' })).toBeVisible();

    await page.getByRole('button', { name: 'Archi' }).click();
    await page.getByRole('button', { name: 'Sign in to workspace' }).click();

    await expect(page).toHaveURL(/\/analyze$/, { timeout: 15000 });
  });

  test('renders cleanly across viewports without horizontal scrollbar overflow', async ({ page }) => {
    for (const width of [1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto('/login');
      await expect(page.locator('#narrative-heading')).toBeVisible();

      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      const innerWidth = await page.evaluate(() => window.innerWidth);
      expect(scrollWidth <= innerWidth, `Overflow detected at ${width}px`).toBe(true);
    }
  });

  test('captures visual artifact screenshots', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto('/login');
    await expect(page.locator('#narrative-heading')).toBeVisible();
    await page.screenshot({ path: '../../artifacts/login/login-desktop.png', fullPage: true });

    await page.setViewportSize({ width: 390, height: 900 });
    await page.goto('/login');
    await expect(page.locator('#narrative-heading')).toBeVisible();
    await page.screenshot({ path: '../../artifacts/login/login-mobile.png', fullPage: true });
  });

  test('clicking analyze buttons opens login page first when unauthenticated', async ({ page }) => {
    // Clear any previous session
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.context().clearCookies();
    await page.goto('/');

    // 1. Header CTA "Start an analysis"
    const headerCta = page.locator('header.platform-header').getByRole('link', { name: /Start an analysis/ });
    await expect(headerCta).toBeVisible();
    await headerCta.click();
    await expect(page).toHaveURL(/\/login\?redirect=%2Fanalyze$/);

    // 2. Return to home and click hero CTA "Start with live evidence"
    await page.goto('/');
    const heroBtn = page.getByRole('link', { name: /Start with live evidence/ });
    await expect(heroBtn).toBeVisible();
    await heroBtn.click();
    await expect(page).toHaveURL(/\/login\?redirect=%2Fanalyze$/);

    // 3. Log in with fast-track demo credentials
    await page.getByRole('button', { name: 'Yorayriniwnl' }).click();
    await page.getByRole('button', { name: 'Sign in to workspace' }).click();

    // 4. Must redirect to destination /analyze
    await expect(page).toHaveURL(/\/analyze$/, { timeout: 15000 });
  });

  test('clicking GitHub OAuth triggers auth endpoint and informs user if keys need configuring', async ({ page }) => {
    await page.goto('/login');
    const githubBtn = page.getByRole('button', { name: 'Continue with GitHub' });
    await expect(githubBtn).toBeVisible();
    await githubBtn.click();

    // When client id is not configured yet, it routes with error=missing_credentials and displays guidance
    await expect(page).toHaveURL(/error=missing_credentials/);
    await expect(page.getByTestId('login-error')).toContainText('GitHub OAuth requires GITHUB_CLIENT_ID');
  });
});
