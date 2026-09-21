import { test, expect } from '@playwright/test';

test('the root route is a command center for every product surface', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: /candidate intelligence/i })).toBeVisible();

  for (const destination of [
    ['Live Evidence', '/analyze'],
    ['Evaluation Workspace', '/workspace'],
    ['Hiring View', '/hr'],
    ['Research Lab', '/research-demo'],
  ] as const) {
    await expect(page.getByRole('link', { name: new RegExp(destination[0], 'i') }).first()).toHaveAttribute('href', destination[1]);
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
  await page.getByRole('link', { name: 'Research Lab', exact: true }).last().click();
  await expect(page).toHaveURL(/\/research-demo$/);
});

test('public routes state what they are and keep a path back to the command center', async ({ page }) => {
  const routes = [
    ['/analyze', /Live Evidence/i, /Live workflow/i],
    ['/research-demo', /Research Lab/i, /Synthetic only/i],
    ['/hr', /Hiring View/i, /Sample workspace/i],
  ] as const;

  for (const [route, surface, status] of routes) {
    await page.goto(route);
    await expect(page.getByRole('link', { name: 'Home', exact: true })).toHaveAttribute('href', '/');
    await expect(page.getByText(surface).first()).toBeVisible();
    await expect(page.getByText(status).first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});

test('workspace keeps its dense tools but provides a shared escape route on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/workspace');
  await expect(page.getByRole('link', { name: /CandidateX/i }).first()).toHaveAttribute('href', '/');
  await expect(page.getByText(/Evaluation Workspace/i).first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('comparison view does not emit duplicate React keys', async ({ page }) => {
  const duplicateKeyErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error' && /same key/i.test(message.text())) {
      duplicateKeyErrors.push(message.text());
    }
  });

  await page.goto('/workspace');
  await page.getByRole('button', { name: 'Compare', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Candidate Comparative Capability Matrix' })).toBeVisible();
  expect(duplicateKeyErrors).toEqual([]);
});
