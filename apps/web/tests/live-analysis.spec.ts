import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';

const pdf = execFileSync('python', ['-c', `import sys,pymupdf
d=pymupdf.open();p=d.new_page();p.insert_text((50,50),'Example Candidate\\nSkills\\nPython, SQL\\nA public technical portfolio.')
sys.stdout.buffer.write(d.tobytes());d.close()`]);
const docx = execFileSync('python', ['-c', `import sys,io,docx
d=docx.Document();d.add_table(rows=1,cols=1).cell(0,0).text='Example Candidate'
for text in ['Professional Summary','Developer building public applications.','Skills','Python, CI/CD','Currently Learning: Docker','Projects','Example API','Built a web application.','Education','B.Tech Computer Science','Certifications','Python Programming Certificate','Experience','Software developer on a personal project.']:
 d.add_paragraph(text)
 s=io.BytesIO();d.save(s);sys.stdout.buffer.write(s.getvalue())`]);

test('real upload, extracted claims, unknown assessment, and export work through the API', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/analyze');
  await expect(page).toHaveURL(/\/analyze$/);
  await page.locator('#resume-upload').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: pdf });
  await expect(page.getByRole('heading', { name: 'Example Candidate', exact: true })).toBeVisible();
  await expect(page.getByTestId('declared-skills')).toContainText('Python');
  await page.getByRole('button', { name: 'Continue to target role' }).click();
  await page.getByRole('button', { name: 'Continue to public sources' }).click();
  await page.getByRole('button', { name: 'Continue to review' }).click();
  await page.getByRole('button', { name: 'Start live analysis' }).click();
  await expect(page.getByRole('heading', { name: 'Example Candidate', exact: true })).toBeVisible();
  await expect(page.getByText('No public sources were selected for this run.', { exact: false })).toBeVisible();
  await expect(page.getByText('Analysis completed with gaps', { exact: true })).toBeVisible();
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

test('invalid upload is visible and a failed rerun keeps the prior dossier clearly identified', async ({ page }) => {
  await page.goto('/analyze');
  await page.locator('#resume-upload').setInputFiles({ name: 'invalid.pdf', mimeType: 'application/pdf', buffer: Buffer.from('invalid') });
  await expect(page.getByRole('alert').filter({ hasText: /document|PDF|file/i })).toBeVisible();
  await page.locator('#resume-upload').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: pdf });
  await expect(page.getByRole('heading', { name: 'Example Candidate' })).toBeVisible();
  await page.getByRole('button', { name: 'Continue to target role' }).click();
  await page.getByRole('button', { name: 'Continue to public sources' }).click();
  await page.getByRole('button', { name: 'Continue to review' }).click();
  await page.getByRole('button', { name: 'Start live analysis' }).click();
  await expect(page.getByRole('region', { name: 'Live candidate dossier' })).toBeVisible();
  await page.getByRole('button', { name: /New evaluation/ }).click();
  await page.locator('#resume-upload').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: pdf });
  await page.getByRole('button', { name: 'Continue to target role' }).click();
  await page.getByRole('button', { name: 'Continue to public sources' }).click();
  await page.getByRole('button', { name: 'Continue to review' }).click();
  await page.route('**/api/live/analyze', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Live backend unavailable.' }) }));
  await page.getByRole('button', { name: 'Start live analysis' }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Live backend unavailable' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Live candidate dossier' })).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'The previous dossier is still shown' })).toBeVisible();
});

test('mobile upload and review stay within viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/analyze');
  await page.locator('#resume-upload').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: pdf });
  await expect(page.getByRole('heading', { name: 'Example Candidate' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/live-analysis-mobile.png' });
});

test('DOCX sections, public-link failures, skill filters and detailed export', async ({ page }) => {
  await page.goto('/analyze');
  await page.locator('#resume-upload').setInputFiles({ name: 'detailed resume.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: docx });
  await expect(page.getByRole('heading', { name: 'Example Candidate', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Continue to target role' }).click();
  await page.getByRole('button', { name: 'Continue to public sources' }).click();
  await page.getByLabel('Add a public source URL').fill('http://127.0.0.1/private');
  await page.getByRole('button', { name: 'Add source' }).click();
  await expect(page.getByRole('checkbox', { name: /http:\/\/127\.0\.0\.1\/private/ })).toBeChecked();
  await page.getByRole('button', { name: 'Continue to review' }).click();
  await page.getByRole('button', { name: 'Start live analysis' }).click();
  await expect(page.getByRole('heading', { name: 'Skills and supporting evidence' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Certificates and credentials' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Python Programming Certificate' })).toBeVisible();
  await expect(page.getByText('security blocked', { exact: true })).toBeVisible();
  await page.getByLabel('Find a skill').fill('Docker');
  await expect(page.locator('summary').filter({ hasText: 'Docker · not observed · Currently learning' })).toBeVisible();
  await page.getByLabel('Show skills without repository evidence').check();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export dossier JSON' }).click();
  const stream = await (await downloadPromise).createReadStream();
  const chunks: Buffer[] = []; for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
  const data = JSON.parse(Buffer.concat(chunks).toString());
  expect(data.analysis.credentials[0].status).toBe('unverified');
  expect(data.analysis.education[0].claim).toBe('B.Tech Computer Science');
  expect(data.analysis.skills.find((s: { skill: string }) => s.skill === 'Docker').learning).toBe(true);
  expect(data.sources[0].status).toBe('security_blocked');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
