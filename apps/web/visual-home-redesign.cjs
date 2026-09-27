const { chromium, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

(async () => {
  const dir = path.resolve(__dirname, '../../artifacts/home-redesign');
  fs.mkdirSync(dir, { recursive: true });
  const browser = await chromium.launch({ channel: 'chromium' });
  const errors = [];
  const viewports = [];
  const url = process.env.VISUAL_BASE_URL || 'http://127.0.0.1:3109';
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    for (const width of [1440, 1024, 390, 320]) {
      await page.setViewportSize({ width, height: width < 500 ? 844 : 1000 });
      await page.goto(url, { waitUntil: 'networkidle' });
      await expect(page.getByTestId('signal-observatory')).toHaveAttribute('data-ready', 'true');
      await page.waitForTimeout(1400);
      await page.getByRole('button', { name: 'Pause 3D animation' }).click();
      await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
      await page.screenshot({ path: path.join(dir, `home-${width}.png`), fullPage: true });
      if (width === 1440 || width === 390) await page.screenshot({ path: path.join(dir, `hero-${width}.png`) });
      const dimensions = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
      if (dimensions.scrollWidth > width) throw new Error(`Horizontal overflow at ${width}`);
      viewports.push(dimensions);
    }

    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(url, { waitUntil: 'networkidle' });
    for (const [name, filename] of [['Look at the work', 'source-example.png'], ['Ask a better question', 'interview-example.png']]) {
      await page.getByRole('tab', { name: new RegExp(name) }).click();
      await page.waitForTimeout(400);
      await page.getByRole('tabpanel').locator('..').screenshot({ path: path.join(dir, filename) });
    }
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(url, { waitUntil: 'networkidle' });
    await expect(page.getByTestId('signal-observatory')).toHaveAttribute('data-ready', 'true');
    await page.screenshot({ path: path.join(dir, 'reduced-motion.png') });
    await page.close();

    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, recordVideo: { dir, size: { width: 1440, height: 1000 } } });
    const motion = await context.newPage();
    motion.on('pageerror', error => errors.push(error.message));
    await motion.goto(url, { waitUntil: 'networkidle' });
    await expect(motion.getByTestId('signal-observatory')).toHaveAttribute('data-ready', 'true');
    await motion.waitForTimeout(1600);
    await motion.mouse.move(1120, 390, { steps: 40 });
    for (const name of ['02 Evidence', '03 Capability', '04 Interview']) {
      await motion.getByRole('button', { name }).click();
      await motion.mouse.move(980, 420, { steps: 30 });
      await motion.waitForTimeout(1300);
    }
    const video = motion.video();
    await context.close();
    await video.saveAs(path.join(dir, 'home-motion.webm'));
    await video.delete();
    if (errors.length) throw new Error(JSON.stringify(errors));
    const report = { url, errors, viewports, video: 'home-motion.webm' };
    fs.writeFileSync(path.join(dir, 'visual-report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
