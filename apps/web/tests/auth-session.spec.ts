import { test, expect } from '@playwright/test';
import { test as authenticatedTest } from './fixtures';

authenticatedTest('a signed session opens analysis before the profile cache is populated', async ({ page }) => {
  let releaseSession!: () => void;
  let sessionRequested!: () => void;
  const sessionGate = new Promise<void>(resolve => { releaseSession = resolve; });
  const requested = new Promise<void>(resolve => { sessionRequested = resolve; });
  await page.route('**/api/auth/session', async route => {
    sessionRequested();
    await sessionGate;
    await route.continue();
  });

  try {
    await page.goto('/analyze');
    await requested;
    await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    expect(await page.evaluate(() => sessionStorage.getItem('cx_user_profile_cache'))).toBeNull();
    await expect(page).toHaveURL(/\/analyze$/);
  } finally {
    releaseSession();
  }

  await expect(page.locator('header.platform-header').getByText('studio-review', { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/\/analyze$/);
  await expect(page.getByRole('heading', { name: 'Build a candidate dossier.' })).toBeVisible();
});

test('reading an absent session does not send a server sign-out request', async ({ page }) => {
  const signouts: string[] = [];
  page.on('request', request => {
    if (new URL(request.url()).pathname === '/api/auth/signout') signouts.push(request.method());
  });
  const sessionResponse = page.waitForResponse('**/api/auth/session');
  await page.goto('/login');
  expect(await (await sessionResponse).json()).toEqual({ user: null });
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  expect(signouts).toEqual([]);
});

authenticatedTest('explicit sign-out invalidates the signed cookie and leaves analysis', async ({ page }) => {
  await page.goto('/analyze');
  const signout = page.waitForResponse('**/api/auth/signout');
  await page.locator('header.platform-header').getByRole('button', { name: 'Sign out', exact: true }).click();
  expect((await signout).ok()).toBe(true);
  await expect(page).toHaveURL(/\/login\?redirect=%2Fanalyze$/);
  expect(await (await page.request.get('/api/auth/session')).json()).toEqual({ user: null });
});
