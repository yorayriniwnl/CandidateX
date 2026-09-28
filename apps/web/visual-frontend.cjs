const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const dir = path.resolve(__dirname, '../../artifacts/frontend-redesign');
  fs.mkdirSync(dir, { recursive: true });
  const url = process.env.VISUAL_BASE_URL || 'http://127.0.0.1:3000';
  const browser = await chromium.launch({ channel: 'chromium' });
  const errors = [];
  const layouts = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    await page.context().addCookies([{ name: 'cx_auth', value: 'studio-review%40example.invalid', url }]);
    page.on('pageerror', error => errors.push(error.message));
    for (const route of ['analyze', 'hr', 'workspace', 'research-demo', 'login']) {
      for (const width of [1440, 1024, 768, 390, 320]) {
        await page.setViewportSize({ width, height: width < 500 ? 844 : 1000 });
        await page.goto(`${url}/${route}`, { waitUntil: 'networkidle' });
        await page.locator('main').waitFor();
        await page.waitForTimeout(700);
        const overflow = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
          elements: [...document.querySelectorAll('main *')].filter(el => el.getBoundingClientRect().right > innerWidth + 1 && getComputedStyle(el).position !== 'fixed').slice(0, 12).map(el => ({ tag: el.tagName, class: el.className, text: el.textContent.slice(0, 50) })) }));
        layouts.push({ route, ...overflow });
        if ([1440, 390].includes(width)) await page.screenshot({ path: path.join(dir, `${route}-${width}.png`), animations: 'disabled' });
        console.log(JSON.stringify({ route, width, scrollWidth: overflow.scrollWidth }));
      }
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`${url}/hr`, { waitUntil: 'networkidle' });
    await page.getByRole('button', { name: 'Add Candidate', exact: true }).click();
    await expect(page.getByRole('dialog', { name: 'Add Candidate', exact: true })).toBeVisible();
    await page.screenshot({ path: path.join(dir, 'add-candidate.png') });
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button', { name: 'Add Candidate', exact: true })).toBeFocused();

    await page.goto(`${url}/workspace`, { waitUntil: 'networkidle' });
    for (const [name, file] of [['New Evaluation Run pipeline', 'workspace-evaluation'], ['Compare Side by side', 'workspace-compare'], ['Methodology Math & proofs', 'workspace-methodology']]) {
      await page.getByRole('button', { name, exact: true }).click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(dir, `${file}.png`), animations: 'disabled' });
    }
    const report = { url, errors, layouts };
    fs.writeFileSync(path.join(dir, 'layout-report.json'), JSON.stringify(report, null, 2));
    if (errors.length || layouts.some(item => item.scrollWidth > item.width)) throw new Error('See layout-report.json for runtime errors or overflow.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
