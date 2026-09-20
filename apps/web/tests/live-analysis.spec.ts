import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';

const pdf = execFileSync('python', ['-c', `import sys,pymupdf
d=pymupdf.open();p=d.new_page();p.insert_text((50,50),'Example Candidate\\nSkills\\nPython, SQL\\nA public technical portfolio.')
sys.stdout.buffer.write(d.tobytes());d.close()`]);

test('real upload, extracted claims, unknown assessment, and export work through the API', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page).toHaveURL(/\/analyze$/);
  await page.getByLabel('Upload resume').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: pdf });
  await expect(page.getByRole('heading', { name: 'Example Candidate', exact: true })).toBeVisible();
  await expect(page.getByText('Python', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Fetch live evidence & analyze' }).click();
  await expect(page.getByRole('heading', { name: 'Technical evidence dossier' })).toBeVisible();
  await expect(page.getByText('No public sources were selected.')).toBeVisible();
  await expect(page.getByText('Insufficient evidence for a broad assessment.', { exact: false })).toBeVisible();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export dossier JSON' }).click();
  const download = await downloadPromise;
  const stream = await download.createReadStream();
  const chunks: Buffer[] = []; for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
  const data = JSON.parse(Buffer.concat(chunks).toString());
  expect(data.dossier.evidence_mode).toBe('live');
  expect(data.dossier.rci).toBeNull();
  expect(data.dossier.evidence_records).toEqual([]);
  expect(data.intake.manifest.display_name).toBe('Example Candidate');
  expect(data.intake.document_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(errors).toEqual([]);
  await page.screenshot({ path: 'test-results/live-analysis-desktop.png', fullPage: true });
});

test('invalid upload and backend errors are visible with no stale dossier', async ({ page }) => {
  await page.goto('/analyze');
  await page.getByLabel('Upload resume').setInputFiles({ name: 'invalid.pdf', mimeType: 'application/pdf', buffer: Buffer.from('invalid') });
  await expect(page.getByRole('alert').filter({ hasText: /document|PDF|file/i })).toBeVisible();
  await page.getByLabel('Upload resume').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: pdf });
  await expect(page.getByRole('heading', { name: 'Example Candidate' })).toBeVisible();
  await page.getByRole('button', { name: 'Fetch live evidence & analyze' }).click();
  await expect(page.getByRole('heading', { name: 'Technical evidence dossier' })).toBeVisible();
  await page.route('**/api/live/analyze', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Live backend unavailable.' }) }));
  await page.getByRole('button', { name: 'Fetch live evidence & analyze' }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Live backend unavailable' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Technical evidence dossier' })).toHaveCount(0);
});

test('mobile upload and review stay within viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/analyze');
  await page.getByLabel('Upload resume').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: pdf });
  await expect(page.getByRole('heading', { name: 'Example Candidate' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/live-analysis-mobile.png' });
});
