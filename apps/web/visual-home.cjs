const { chromium, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

(async () => {
  const dir = path.resolve(__dirname, '../../artifacts/home-scene');
  fs.mkdirSync(dir, { recursive: true });
  const browser = await chromium.launch({ channel: 'chromium' });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, recordVideo: { dir, size: { width: 1440, height: 1000 } } });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto(process.env.VISUAL_BASE_URL || 'http://127.0.0.1:3002');
  const scene = page.getByTestId('signal-observatory');
  await expect(scene).toHaveAttribute('data-ready', 'true');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(dir, 'desktop-1440.png') });
  for (const point of [[1100, 350], [1280, 500], [930, 560], [1140, 380]]) {
    await page.mouse.move(...point, { steps: 30 });
    await page.waitForTimeout(1000);
  }
  await page.mouse.move(20, 100);
  await page.waitForTimeout(1000);
  const video = page.video();
  await context.close();
  await video.saveAs(path.join(dir, 'home-motion.webm'));
  await video.delete();

  const inspection = await browser.newPage();
  inspection.on('pageerror', error => errors.push(error.message));
  inspection.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  for (const width of [1280, 1024, 390]) {
    await inspection.setViewportSize({ width, height: 1000 });
    await inspection.goto(process.env.VISUAL_BASE_URL || 'http://127.0.0.1:3002');
    const engine = inspection.getByTestId('signal-observatory');
    await engine.scrollIntoViewIfNeeded();
    await expect(engine).toHaveAttribute('data-ready', 'true');
    await inspection.getByRole('button', { name: 'Pause 3D animation' }).click();
    await inspection.screenshot({ path: path.join(dir, `scene-${width}.png`) });
    if (await inspection.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error(`Overflow at ${width}`);
  }
  await inspection.emulateMedia({ reducedMotion: 'reduce' });
  await inspection.setViewportSize({ width: 1280, height: 1000 });
  await inspection.goto(process.env.VISUAL_BASE_URL || 'http://127.0.0.1:3002');
  await expect(inspection.getByTestId('signal-observatory')).toHaveAttribute('data-ready', 'true');
  await expect(inspection.getByRole('button', { name: 'Play 3D animation' })).toBeVisible();
  await inspection.screenshot({ path: path.join(dir, 'reduced-motion.png') });
  if (errors.length) throw new Error(JSON.stringify(errors));
  console.log(JSON.stringify({ errors, viewports: [1440, 1280, 1024, 390], video: 'artifacts/home-scene/home-motion.webm' }));
  await browser.close();
})();
