import { expect, test } from '@playwright/test';

test('landing page introduces Evidence OS and routes to live analysis and synthetic research', async ({ page }) => {
  await page.goto('/');

  await expect(page).toHaveTitle(/CandidateX/i);
  await expect(page.getByRole('heading', { name: 'Evidence before interviews.' })).toBeVisible();
  await expect(page.getByText('Static analysis. Traceable evidence. Explicit unknowns.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Analyze candidate' })).toHaveAttribute('href', '/analyze');
  await expect(page.getByRole('link', { name: 'View research demo' })).toHaveAttribute('href', '/research-demo');
  await expect(page.locator('main')).not.toContainText(/AI-powered|verified skill|hiring recommendation/i);
  await page.screenshot({ path: 'test-results/evidence-os-landing-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/evidence-os-landing-mobile.png', fullPage: true });
});
