import { test, expect } from '@playwright/test';

test('engine stages explain the process and still work with reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const engine = page.getByTestId('signal-observatory');
  await expect(engine).toHaveAttribute('data-ready', 'true');
  const before = await engine.locator('canvas').screenshot();
  await engine.getByRole('button', { name: '04 Interview' }).click();
  await expect(engine.getByRole('button', { name: '04 Interview' })).toHaveAttribute('aria-pressed', 'true');
  await expect(engine).toContainText('Turn what is unknown into a better question.');
  expect((await engine.locator('canvas').screenshot()).equals(before)).toBe(false);
  await expect(engine).toHaveAttribute('data-motion', 'paused');
});

test('the example follows a claim through evidence to an interview using the keyboard', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  const panel = page.getByRole('tabpanel');
  await expect(panel).toContainText('Built a fault-tolerant');
  await page.getByRole('tab', { name: /Start with the claim/ }).focus();
  await page.keyboard.press('ArrowDown');
  await expect(page.getByRole('tab', { name: /Look at the work/ })).toBeFocused();
  await expect(panel).toContainText('Production behavior unknown');
  await page.keyboard.press('ArrowDown');
  await expect(panel).toContainText('What happens when a payment succeeds');
  await page.getByRole('button', { name: 'Restart example' }).click();
  await expect(panel).toContainText('Candidate résumé');
  await page.getByRole('link', { name: /Follow your own evidence/ }).click();
  await expect(page).toHaveURL(/\/analyze$/);
  expect(errors).toEqual([]);
});

test('home remains within the viewport and the mobile menu works', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.getByTestId('signal-observatory')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `overflow at ${width}`).toBe(true);
    if (width === 390) {
      const sceneTop = await page.getByTestId('signal-observatory').evaluate(element => element.getBoundingClientRect().top);
      expect(sceneTop).toBeLessThan(650);
    }
    await page.getByRole('tab', { name: /Look at the work/ }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `code overflow at ${width}`).toBe(true);
  }
  await page.getByRole('button', { name: 'Toggle navigation' }).click();
  await expect(page.getByRole('button', { name: 'Toggle navigation' })).toHaveAttribute('aria-expanded', 'true');
  await page.getByRole('navigation', { name: 'Primary navigation' }).getByRole('link', { name: 'Live Evidence' }).click();
  await expect(page).toHaveURL(/\/analyze$/);
});
