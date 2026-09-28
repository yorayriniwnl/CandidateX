import { test, expect } from '@playwright/test';
import { changedPixels } from './pixel-difference';

test('home scene animates, pauses without drift, and resumes', async ({ page }) => {
  await page.goto('/');
  const scene = page.getByTestId('signal-observatory');
  await scene.scrollIntoViewIfNeeded();
  await expect(scene).toHaveAttribute('data-ready', 'true');
  const canvas = scene.locator('canvas');
  await expect(canvas).toHaveCSS('opacity', '1');
  const first = await canvas.screenshot();
  await expect.poll(async () => changedPixels(page, first, await canvas.screenshot())).toBeGreaterThan(100);
  await page.getByRole('button', { name: 'Pause 3D animation' }).click();
  const paused = await canvas.screenshot();
  await page.waitForTimeout(250);
  expect(await changedPixels(page, paused, await canvas.screenshot())).toBeLessThan(5);
  await page.getByRole('button', { name: 'Play 3D animation' }).click();
  await expect.poll(async () => changedPixels(page, paused, await canvas.screenshot())).toBeGreaterThan(100);
  await page.getByRole('link', { name: /Start with live evidence/ }).click();
  await expect(page).toHaveURL(/\/login|\/analyze$/);
});

test('reduced motion renders a still scene and responds to preference changes', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const scene = page.getByTestId('signal-observatory');
  await scene.scrollIntoViewIfNeeded();
  await expect(scene).toHaveAttribute('data-ready', 'true');
  await expect(page.getByRole('button', { name: 'Play 3D animation' })).toBeVisible();
  const canvas = scene.locator('canvas');
  await expect(canvas).toHaveCSS('opacity', '1');
  const still = await canvas.screenshot();
  await page.waitForTimeout(250);
  expect(await changedPixels(page, still, await canvas.screenshot())).toBeLessThan(5);
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await expect(page.getByRole('button', { name: 'Pause 3D animation' })).toBeVisible();
  await expect.poll(async () => changedPixels(page, still, await canvas.screenshot())).toBeGreaterThan(100);
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
  await scene.scrollIntoViewIfNeeded();
  await expect(scene.locator('[data-renderer="fallback"]')).toBeVisible();
  await expect(scene.locator('svg[viewBox="0 0 600 520"]')).toBeVisible();
  await expect(scene.locator('canvas')).toHaveCount(0);
  await expect(page.getByRole('button', { name: /3D animation/ })).toHaveCount(0);
  expect(errors).toEqual([]);
  await page.getByRole('link', { name: /Start with live evidence/ }).click();
  await expect(page).toHaveURL(/\/login|\/analyze$/);
});

test('losing the WebGL context restores the static illustration', async ({ page }) => {
  await page.goto('/');
  const scene = page.getByTestId('signal-observatory');
  await scene.scrollIntoViewIfNeeded();
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

test('user can click and rotate 360 degrees and scene smoothly returns upon releasing left click', async ({ page }) => {
  await page.goto('/');
  const scene = page.getByTestId('signal-observatory');
  await scene.scrollIntoViewIfNeeded();
  await expect(scene).toHaveAttribute('data-ready', 'true');

  await page.getByRole('button', { name: 'Pause 3D animation' }).click();
  const canvas = scene.locator('canvas');
  const stage = scene.locator('[class*="stage"]').first();
  const box = await canvas.boundingBox();
  if (!box) throw new Error('Canvas bounding box not found');

  const centerX = box.x + box.width / 2;
  const centerY = box.y + box.height / 2;

  const getLabelsTransform = () => scene.locator('[class*="nodeLabel"]').evaluateAll(els => els.map(e => (e as HTMLElement).style.transform));
  const initialLabels = await getLabelsTransform();

  await page.mouse.move(centerX, centerY);
  await expect(stage).toHaveCSS('cursor', 'grab');

  await page.mouse.down({ button: 'left' });
  await expect(stage).toHaveAttribute('data-dragging', 'true');
  await expect(stage).toHaveCSS('cursor', 'grabbing');

  await page.mouse.move(centerX + 200, centerY, { steps: 10 });
  const rotatedLabels = await getLabelsTransform();
  expect(rotatedLabels).not.toEqual(initialLabels);

  await page.mouse.move(centerX + 400, centerY, { steps: 10 });
  const fullRotatedLabels = await getLabelsTransform();
  expect(fullRotatedLabels).not.toEqual(rotatedLabels);

  await page.mouse.up({ button: 'left' });
  await expect(stage).not.toHaveAttribute('data-dragging', 'true');

  await expect.poll(getLabelsTransform, { timeout: 4000 }).toEqual(initialLabels);
});

test('right-clicking the scene triggers surprise overdrive, theme cycling, and HUD badge', async ({ page }) => {
  await page.goto('/');
  const scene = page.getByTestId('signal-observatory');
  await scene.scrollIntoViewIfNeeded();
  await expect(scene).toHaveAttribute('data-ready', 'true');

  const canvas = scene.locator('canvas');
  await canvas.click({ button: 'right' });

  const badge = scene.getByTestId('signal-surprise-badge');
  await expect(badge).toBeVisible();
  const firstBadgeText = await badge.textContent();
  expect(firstBadgeText).toContain('SOLAR SUPERNOVA');
  expect(firstBadgeText).toContain('Thermonuclear surge');

  // Triggering right-click again cycles to next theme
  await canvas.click({ button: 'right' });
  await expect(badge).toContainText('CYBER EMERALD');
  const secondBadgeText = await badge.textContent();
  expect(secondBadgeText).toContain('CYBER EMERALD');
  expect(secondBadgeText).toContain('Matrix verification');
});
