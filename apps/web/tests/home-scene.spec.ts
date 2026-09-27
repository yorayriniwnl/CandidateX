import { test, expect } from '@playwright/test';

test('home scene animates, pauses without drift, and resumes', async ({ page }) => {
  test.setTimeout(45000);
  await page.goto('/');
  const scene = page.getByTestId('signal-observatory');
  const stage = scene.getByTestId('signal-scene');
  await stage.scrollIntoViewIfNeeded();
  await expect(scene).toHaveAttribute('data-ready', 'true');
  const canvas = scene.locator('canvas');
  const first = await canvas.screenshot();
  await expect.poll(async () => (await canvas.screenshot()).equals(first), { timeout: 15000 }).toBe(false);
  await page.getByRole('button', { name: 'Pause 3D animation' }).click();
  const paused = await canvas.screenshot();
  await page.waitForTimeout(250);
  expect((await canvas.screenshot()).equals(paused)).toBe(true);
  await page.getByRole('button', { name: 'Play 3D animation' }).click();
  await stage.scrollIntoViewIfNeeded();
  await expect.poll(async () => (await canvas.screenshot()).equals(paused), { timeout: 15000 }).toBe(false);
  await page.getByRole('link', { name: /Start with live evidence/ }).click();
  await expect(page).toHaveURL(/\/analyze$/);
});

test('reduced motion renders a still scene and responds to preference changes', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const scene = page.getByTestId('signal-observatory');
  await scene.getByTestId('signal-scene').scrollIntoViewIfNeeded();
  await expect(scene).toHaveAttribute('data-ready', 'true');
  await expect(page.getByRole('button', { name: 'Play 3D animation' })).toBeVisible();
  const canvas = scene.locator('canvas');
  const still = await canvas.screenshot();
  await page.waitForTimeout(250);
  expect((await canvas.screenshot()).equals(still)).toBe(true);
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await expect(page.getByRole('button', { name: 'Pause 3D animation' })).toBeVisible();
  await expect.poll(async () => (await canvas.screenshot()).equals(still), { timeout: 15000 }).toBe(false);
});

test('home keeps an illustration and working navigation without WebGL', async ({ page }) => {
  await page.addInitScript(() => {
    const getContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, type: string, ...args: unknown[]) {
      if (type.startsWith('webgl')) return null;
      return Reflect.apply(getContext, this, [type, ...args]);
    } as typeof getContext;
  });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  const scene = page.getByTestId('signal-observatory');
  await scene.getByTestId('signal-scene').scrollIntoViewIfNeeded();
  await expect(scene.locator('[data-renderer="fallback"]')).toBeVisible();
  await expect(scene.locator('svg[viewBox="0 0 600 520"]')).toBeVisible();
  await expect(scene.locator('canvas')).toHaveCount(0);
  await expect(page.getByRole('button', { name: /3D animation/ })).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.getByRole('link', { name: /Start with live evidence/ }).click();
  await expect(page).toHaveURL(/\/analyze$/);
});

test('losing the WebGL context restores the static illustration', async ({ page }) => {
  await page.goto('/');
  const scene = page.getByTestId('signal-observatory');
  await scene.getByTestId('signal-scene').scrollIntoViewIfNeeded();
  await expect(scene).toHaveAttribute('data-ready', 'true');
  await scene.locator('canvas').evaluate((canvas: HTMLCanvasElement) => {
    const extension = canvas.getContext('webgl2')?.getExtension('WEBGL_lose_context');
    if (!extension) throw new Error('Context-loss simulation unavailable');
    extension.loseContext();
  });
  await expect(scene).toHaveAttribute('data-ready', 'false');
  await expect(scene.locator('svg[viewBox="0 0 600 520"]')).toBeVisible();
  await expect(scene.locator('canvas')).toBeHidden();
  await expect(page.getByRole('button', { name: /3D animation/ })).toHaveCount(0);
});
