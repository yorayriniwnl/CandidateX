const { chromium, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const dir = path.resolve(__dirname, '../../artifacts/frontend-redesign');
  const fixtures = process.env.VISUAL_FIXTURE_DIR
    ? path.resolve(process.env.VISUAL_FIXTURE_DIR)
    : path.resolve(__dirname, '../../artifacts/result-redesign');
  for (const file of ['live-result.json', 'resume.pdf']) {
    if (!fs.existsSync(path.join(fixtures, file))) {
      throw new Error(`Missing ${file}. Set VISUAL_FIXTURE_DIR to a local saved analysis response and its resume. See artifacts/frontend-redesign/README.md.`);
    }
  }
  fs.mkdirSync(dir, { recursive: true });
  const result = JSON.parse(fs.readFileSync(path.join(fixtures, 'live-result.json'), 'utf8'));
  const url = process.env.VISUAL_BASE_URL || 'http://127.0.0.1:3109';
  const browser = await chromium.launch({ channel: 'chromium' });
  const errors = [];
  const layouts = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    await page.context().addCookies([{ name: 'cx_auth', value: 'studio-review%40example.invalid', url }]);
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/live/intake', route => route.fulfill({ json: result.intake }));
    let completeAnalysis;
    const analysisGate = new Promise(resolve => { completeAnalysis = resolve; });
    await page.route('**/api/live/analyze', async route => { await analysisGate; await route.fulfill({ json: result }); });
    await page.goto(`${url}/analyze`);
    await page.locator('#resume-upload').setInputFiles(path.join(fixtures, 'resume.pdf'));
    for (const [name, file] of [['Continue to target role', 'role'], ['Continue to public sources', 'sources'], ['Continue to review', 'review']]) {
      await page.getByRole('button', { name, exact: true }).click();
      for (const width of [1440, 390]) {
        await page.setViewportSize({ width, height: 1000 });
        await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
        await page.screenshot({ animations: 'disabled', path: path.join(dir, `analysis-${file}-${width}.png`) });
        layouts.push({ step: file, width, scrollWidth: await page.evaluate(() => document.documentElement.scrollWidth) });
      }
      await page.setViewportSize({ width: 1440, height: 1000 });
    }
    await page.getByRole('button', { name: 'Start live analysis', exact: true }).click();
    await expect(page.getByText('Waiting for the live analysis response', { exact: true })).toBeVisible();
    await page.screenshot({ path: path.join(dir, 'analysis-running.png') });
    completeAnalysis();
    await expect(page.getByRole('region', { name: 'Live candidate dossier', exact: true })).toBeVisible();
    for (const width of [1440, 1024, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
      await page.screenshot({ animations: 'disabled', path: path.join(dir, `dossier-${width}.png`) });
      layouts.push({ step: 'dossier', width, scrollWidth: await page.evaluate(() => document.documentElement.scrollWidth) });
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.locator('#capabilities').getByRole('button', { name: /Backend Engineering/ }).click();
    await page.locator('#capabilities').scrollIntoViewIfNeeded();
    await page.screenshot({ animations: 'disabled', path: path.join(dir, 'dossier-capabilities.png') });
    await page.getByRole('region', { name: 'Observed engineering signals' }).getByRole('button').first().click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.screenshot({ animations: 'disabled', path: path.join(dir, 'evidence-inspector.png') });
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await page.goto(`${url}/research-demo`);
    await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
    await expect(page.getByTestId('result-status')).toHaveText('Completed · synthetic evidence', { timeout: 30000 });
    await page.evaluate(() => window.scrollTo({ top: 460, behavior: 'instant' }));
    await page.screenshot({ animations: 'disabled', path: path.join(dir, 'research-result.png') });
    const report = { url, fixture: 'Replayed supplied local dossier response; research results computed by backend.', errors, layouts };
    fs.writeFileSync(path.join(dir, 'flow-report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
    if (errors.length || layouts.some(item => item.scrollWidth > item.width)) throw new Error('See flow-report.json.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
