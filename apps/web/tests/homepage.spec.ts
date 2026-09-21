import { test, expect } from '@playwright/test';

test('the root route is a command center for the live product surface', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: /candidate intelligence/i })).toBeVisible();

  await expect(page.getByRole('link', { name: 'Live Evidence', exact: true }).first()).toHaveAttribute('href', '/analyze');
});

test('the homepage exposes only the live product surface after prototype retirement', async ({ page, request }) => {
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'Live Evidence', exact: true }).first()).toHaveAttribute('href', '/analyze');
  await expect(page.getByRole('link', { name: /Workspace|Hiring View|Research Lab/i })).toHaveCount(0);

  for (const retiredRoute of ['/workspace', '/hr', '/research-demo']) {
    const response = await request.get(retiredRoute);
    expect(response.status(), `${retiredRoute} should no longer be a product page`).toBe(404);
  }
});

test('the public header exposes active navigation and the analysis CTA', async ({ page }) => {
  await page.goto('/analyze');
  await expect(page.getByRole('link', { name: 'Home', exact: true })).toHaveAttribute('href', '/');
  await expect(page.getByRole('link', { name: 'Live Evidence', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('link', { name: /Start an analysis/i }).first()).toHaveAttribute('href', '/analyze');
});

test('the command center stays usable on mobile and explains the operating loop', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByText(/bring context/i)).toBeVisible();
  await expect(page.getByText(/trace the signal/i)).toBeVisible();
  await expect(page.getByText(/prepare the conversation/i)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  const menu = page.getByRole('button', { name: /toggle navigation/i });
  await expect(menu).toHaveAttribute('aria-expanded', 'false');
  await menu.click();
  await expect(menu).toHaveAttribute('aria-expanded', 'true');
  await page.getByRole('link', { name: 'Live Evidence', exact: true }).last().click();
  await expect(page).toHaveURL(/\/analyze$/);
});

test('the command center keeps the signal observatory in the first tablet viewport', async ({ page }) => {
  await page.setViewportSize({ width: 880, height: 900 });
  await page.goto('/');

  const observatory = page.getByTestId('signal-observatory');
  await expect(observatory).toBeVisible();
  await expect(page.getByText(/candidate claims move through public evidence/i)).toBeAttached();
  const box = await observatory.boundingBox();
  expect(box?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(900);
});

test('public routes state what they are and keep a path back to the command center', async ({ page }) => {
  const routes = [
    ['/analyze', /Live Evidence/i, /Live workflow/i],
  ] as const;

  for (const [route, surface, status] of routes) {
    await page.goto(route);
    await expect(page.getByRole('link', { name: 'Home', exact: true })).toHaveAttribute('href', '/');
    await expect(page.getByText(surface).first()).toBeVisible();
    await expect(page.getByText(status).first()).toBeVisible();
    await expect(page.locator('.observatory-route')).toHaveCount(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});

test('public header keeps its surface label clear at tablet width', async ({ page }) => {
  await page.setViewportSize({ width: 880, height: 900 });

  for (const route of ['/analyze']) {
    await page.goto(route);
    const metrics = await page.evaluate(() => {
      const label = document.querySelector<HTMLElement>('.platform-context__label');
      const navigation = document.querySelector<HTMLElement>('.platform-navigation');
      const toggle = document.querySelector<HTMLElement>('.platform-menu-toggle');
      const labelRect = label?.getBoundingClientRect();
      const navigationRect = navigation?.getBoundingClientRect();
      const navigationVisible = !!navigation && getComputedStyle(navigation).display !== 'none';
      const toggleVisible = !!toggle && getComputedStyle(toggle).display !== 'none';

      return {
        documentOverflow: document.documentElement.scrollWidth > window.innerWidth,
        labelNavigationOverlap: navigationVisible && !!labelRect && !!navigationRect && labelRect.right > navigationRect.left,
        labelOverflow: !!label && label.scrollWidth > label.clientWidth,
        navigationVisible,
        toggleVisible,
      };
    });

    expect(metrics.documentOverflow, `${route} should not overflow horizontally`).toBe(false);
    expect(metrics.labelNavigationOverlap, `${route} surface label should not overlap navigation`).toBe(false);
    expect(metrics.labelOverflow, `${route} surface label should not overflow its container`).toBe(false);
    expect(metrics.navigationVisible || metrics.toggleVisible, `${route} should expose navigation`).toBe(true);
  }
});

test('live evidence keeps the shared header flush with the application shell', async ({ page }) => {
  await page.goto('/analyze');
  const header = page.locator('.platform-header');
  const box = await header.boundingBox();
  expect(box?.x ?? Number.POSITIVE_INFINITY).toBeLessThanOrEqual(1);
  expect(box?.width ?? 0).toBeGreaterThan((await page.evaluate(() => window.innerWidth)) * 0.98);
});
