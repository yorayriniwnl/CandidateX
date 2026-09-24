import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('paper demonstration uses the backend and changes with role, missingness and overrides', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/research-demo');
  await expect(page.getByRole('heading', { name: 'From evidence to interview.' })).toBeVisible();
  await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
  await expect(page.getByTestId('result-status')).toHaveText('Completed · synthetic evidence');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'test-results/research-demo-desktop.png', fullPage: true });
  const baseline = await page.getByTestId('rci-value').innerText();
  await page.getByLabel('Target role').selectOption('frontend');
  await expect(page.getByText('Inputs changed. Run again to update the results.')).toBeVisible();
  await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
  await expect(page.getByTestId('rci-value')).not.toHaveText(baseline);
  await page.getByRole('button', { name: 'Inspect backend engineering evidence' }).click();
  await expect(page.getByTestId('evidence-inspector')).toContainText('SHA-256');
  await expect(page.getByTestId('evidence-inspector')).toContainText('synthetic://');
  await page.getByLabel('Override capability').selectOption('backend_engineering');
  await page.getByRole('button', { name: 'Apply focused override' }).click();
  await expect(page.getByTestId('override-history')).toContainText('Synthetic demonstration weight override');
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export snapshot JSON' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain('candidatex-research');
  const exported = JSON.parse(await readFile((await download.path())!, 'utf8'));
  expect(exported.dossier.evidence_mode).toBe('synthetic');
  expect(exported.benchmark_scope.headline_reproduced).toBe(false);
  expect(exported.graph.analysis_run_id).toBe(exported.dossier.analysis_run_id);
  expect(exported.dossier.override_history.at(-1).justification).toBe('Synthetic demonstration weight override');
  await page.getByLabel('Evidence scenario').selectOption('conflicting');
  await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
  await expect(page.getByTestId('conflict-count')).toHaveText('2');
  await page.getByLabel('Evidence scenario').selectOption('sparse');
  await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
  await expect(page.getByText('Insufficient evidence:', { exact: false })).toBeVisible();
  await page.getByLabel('Ownership multiplier:', { exact: false }).focus();
  await page.getByLabel('Ownership multiplier:', { exact: false }).press('Home');
  await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
  await expect(page.getByTestId('rci-value')).toHaveText('Unknown');
  await page.getByLabel('Evidence scenario').selectOption('empty');
  await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
  await expect(page.getByTestId('rci-value')).toHaveText('Unknown');
  await expect(page.getByTestId('coverage-value')).toHaveText('0.0%');
  expect(errors).toEqual([]);
});

test('failed requests never retain a successful dossier as the new result', async ({ page }) => {
  await page.goto('/research-demo');
  await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
  await expect(page.getByTestId('result-status')).toBeVisible();
  await page.route('**/api/demo', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Backend unavailable. No sample result substituted.' }) }));
  await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Backend unavailable' })).toBeVisible();
  await expect(page.getByTestId('rci-value')).toHaveCount(0);
});

test('mobile controls and evidence table fit within the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/research-demo');
  await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
  await expect(page.getByTestId('result-status')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'test-results/research-demo-mobile.png' });
});

test('public synthetic demo rejects real-data inputs and legacy routes', async ({ page }) => {
  await page.goto('/research-demo');
  await expect(page.getByLabel('Job description')).toHaveCount(0);
  await expect(page.getByLabel('Override justification')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Prototype workspace' })).toHaveCount(0);
  await expect(page.getByText(/generated synthetic observations/i)).toBeVisible();
  await expect(page.getByText(/no resumes or profiles are accepted/i)).toBeVisible();
  await expect(page.getByText(/no real person is assessed/i)).toBeVisible();
  await expect(page.getByText(/not a validated hiring predictor/i)).toBeVisible();
});

test('local legacy workspace remains directly accessible without a demo shortcut', async ({ page }) => {
  await page.goto('/research-demo');
  await expect(page.getByRole('link', { name: 'Prototype workspace' })).toHaveCount(0);
  await page.goto('/workspace');
  await page.getByRole('button', { name: 'Dossier Deep analysis' }).click();
  await expect(page.getByText('No candidate dossier selected or available.')).toBeVisible();
});
