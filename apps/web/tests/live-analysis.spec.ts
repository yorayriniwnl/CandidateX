import { test, expect } from './fixtures';
import { execFileSync } from 'node:child_process';

const pdf = execFileSync('python', ['-c', `import sys,pymupdf
d=pymupdf.open();p=d.new_page();p.insert_text((50,50),'Example Candidate\\nSkills\\nPython, SQL\\nA public technical portfolio.')
sys.stdout.buffer.write(d.tobytes());d.close()`]);
const docx = execFileSync('python', ['-c', `import sys,io,docx
d=docx.Document();d.add_table(rows=1,cols=1).cell(0,0).text='Example Candidate'
for text in ['Professional Summary','Developer building public applications.','Skills','Python, CI/CD','Currently Learning: Docker','Projects','Example API','Built a web application.','Education','B.Tech Computer Science','Certifications','Python Programming Certificate','Experience','Software developer on a personal project.']:
 d.add_paragraph(text)
 s=io.BytesIO();d.save(s);sys.stdout.buffer.write(s.getvalue())`]);
const pdfWithPhoto = execFileSync('python', ['-c', `import sys,io,pymupdf
from PIL import Image
d=pymupdf.open();p=d.new_page()
img=Image.new('RGB',(140,140),color='blue')
buf=io.BytesIO();img.save(buf,format='JPEG')
p.insert_image(pymupdf.Rect(450,50,550,150),stream=buf.getvalue())
p.insert_text((50,50),'Photo Candidate\\nSkills\\nPython, Docker\\nPublic portfolio.')
sys.stdout.buffer.write(d.tobytes());d.close()`]);

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
  await expect(page.getByRole('region', { name: 'Live candidate dossier' }).getByText('No public sources were selected for this run.', { exact: false })).toBeVisible();
  await expect(page.getByText('Insufficient evidence', { exact: true })).toBeVisible();
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
  await page.getByRole('button', { name: /Run another analysis/ }).click();
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
  await page.getByText('Detailed résumé review & job requirements', { exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Skills and supporting evidence' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Certificates and credentials' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Python Programming Certificate' })).toBeVisible();
  await expect(page.getByText('security blocked', { exact: true }).first()).toBeVisible();
  await page.getByLabel('Find a skill').fill('Docker');
  await expect(page.getByRole('region', { name: 'Detailed resume analysis', exact: true }).locator('summary').filter({ hasText: 'Docker' })).toContainText('Currently learning');
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

test('resume with photo extracts and displays picture across intake, dossier header, and review', async ({ page }) => {
  await page.goto('/analyze');
  await page.locator('#resume-upload').setInputFiles({ name: 'photo-resume.pdf', mimeType: 'application/pdf', buffer: pdfWithPhoto });
  await expect(page.getByRole('heading', { name: 'Photo Candidate', exact: true })).toBeVisible();
  await expect(page.getByTestId('resume-picture')).toBeVisible();

  // Test opening lightbox on Step 1:
  await page.getByTestId('resume-picture').click();
  await expect(page.getByTestId('lightbox-large-picture')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Download candidate photo' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('lightbox-large-picture')).not.toBeVisible();

  await page.getByRole('button', { name: 'Continue to target role' }).click();
  await page.getByRole('button', { name: 'Continue to public sources' }).click();
  await page.getByRole('button', { name: 'Continue to review' }).click();
  await page.getByRole('button', { name: 'Start live analysis' }).click();

  await expect(page.getByRole('heading', { name: 'Photo Candidate', exact: true })).toBeVisible();
  await expect(page.getByTestId('dossier-candidate-picture')).toBeVisible();

  // Test opening lightbox on Dossier Header:
  await page.getByTestId('dossier-candidate-picture').click();
  await expect(page.getByTestId('lightbox-large-picture')).toBeVisible();
  await page.getByRole('button', { name: 'Close photo' }).click();
  await expect(page.getByTestId('lightbox-large-picture')).not.toBeVisible();

  await page.getByText('Detailed résumé review & job requirements', { exact: true }).click();
  await expect(page.getByTestId('review-resume-picture')).toBeVisible();

  // Test opening lightbox on Review tab:
  await page.getByTestId('review-resume-picture').click();
  await expect(page.getByTestId('lightbox-large-picture')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('lightbox-large-picture')).not.toBeVisible();

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export dossier JSON' }).click();
  const download = await downloadPromise;
  const stream = await download.createReadStream();
  const chunks: Buffer[] = []; for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
  const data = JSON.parse(Buffer.concat(chunks).toString());
  expect(data.intake.manifest.picture).toMatch(/^data:image\/[a-z]+;base64,/);
});

test('report and full audit export options work correctly across header and provenance section', async ({ page }) => {
  await page.goto('/analyze');
  await page.locator('#resume-upload').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: pdf });
  await expect(page.getByRole('heading', { name: 'Example Candidate', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Continue to target role' }).click();
  await page.getByRole('button', { name: 'Continue to public sources' }).click();
  await page.getByRole('button', { name: 'Continue to review' }).click();
  await page.getByRole('button', { name: 'Start live analysis' }).click();
  await expect(page.getByRole('heading', { name: 'Example Candidate', exact: true })).toBeVisible();

  // 1. Header Dropdown: Full Audit (Markdown)
  const exportMenuButton = page.getByRole('button', { name: 'Export report and audit options' });
  await expect(exportMenuButton).toBeVisible();
  await exportMenuButton.click();

  await expect(page.getByRole('menuitem', { name: 'Download HTML Report' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Download Markdown Report' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Download Full Audit (HTML)' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Download Full Audit (Markdown)' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Download Evidence Ledger (CSV)' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Report + Audit Bundle (MD)' })).toBeVisible();

  const auditMdDownloadPromise = page.waitForEvent('download');
  await page.getByRole('menuitem', { name: 'Download Full Audit (Markdown)' }).click();
  const auditMdDownload = await auditMdDownloadPromise;
  expect(auditMdDownload.suggestedFilename()).toContain('full_audit.md');
  const auditMdStream = await auditMdDownload.createReadStream();
  const auditMdChunks: Buffer[] = [];
  for await (const chunk of auditMdStream!) auditMdChunks.push(Buffer.from(chunk));
  const auditMdContent = Buffer.concat(auditMdChunks).toString();
  expect(auditMdContent).toContain('Candidate Governance & Full Audit Trail: Example Candidate');
  expect(auditMdContent).toContain('Analysis Run ID:');

  // 2. Header Dropdown: Evidence Ledger (CSV)
  await exportMenuButton.click();
  const csvDownloadPromise = page.waitForEvent('download');
  await page.getByRole('menuitem', { name: 'Download Evidence Ledger (CSV)' }).click();
  const csvDownload = await csvDownloadPromise;
  expect(csvDownload.suggestedFilename()).toContain('full_audit.csv');
  const csvStream = await csvDownload.createReadStream();
  const csvChunks: Buffer[] = [];
  for await (const chunk of csvStream!) csvChunks.push(Buffer.from(chunk));
  const csvContent = Buffer.concat(csvChunks).toString();
  expect(csvContent).toContain('Evidence ID');
  expect(csvContent).toContain('Target Capability');

  // 3. Section 08 Methodology / Provenance: Export Full Audit (JSON)
  await page.getByText('Run metadata, versions & limitations', { exact: true }).click();
  const auditSectionExportButton = page.getByRole('button', { name: 'Export full audit options' });
  await expect(auditSectionExportButton).toBeVisible();
  await auditSectionExportButton.click();

  await expect(page.getByRole('menuitem', { name: 'Full Audit (JSON)' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Evidence Ledger (CSV)' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Full Audit (Markdown)' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Full Audit (HTML / Print)' })).toBeVisible();

  const auditJsonDownloadPromise = page.waitForEvent('download');
  await page.getByRole('menuitem', { name: 'Full Audit (JSON)' }).click();
  const auditJsonDownload = await auditJsonDownloadPromise;
  expect(auditJsonDownload.suggestedFilename()).toContain('full_audit.json');
  const auditJsonStream = await auditJsonDownload.createReadStream();
  const auditJsonChunks: Buffer[] = [];
  for await (const chunk of auditJsonStream!) auditJsonChunks.push(Buffer.from(chunk));
  const auditJson = JSON.parse(Buffer.concat(auditJsonChunks).toString());
  expect(auditJson.analysis_run_id).toBeDefined();
  expect(auditJson.candidate_id).toBeDefined();
});
