import { expect, test } from '@playwright/test';

test('hiring dashboard sample mode only renders synthetic candidate identities', async ({ page }) => {
  await page.route('**/api/v1/candidates', (route) => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'Sample-only test outage' }),
  }));

  await page.goto('/hr');

  await expect(page.getByText('Sample workspace.')).toBeVisible();
  const names = await page.locator('tbody th[scope="row"] p.font-semibold').allTextContents();
  expect(names).toEqual([
    'Demo Candidate 01',
    'Demo Candidate 02',
    'Demo Candidate 03',
    'Demo Candidate 04',
    'Demo Candidate 05',
  ]);

  const rendered = await page.locator('body').innerText();
  expect(rendered).not.toMatch(/Ayush Roy|Archi Srivastava|Atmaja Tripathy|Shreshth Nigam|P Ajay Kumar/);
  expect(rendered).not.toMatch(/\b\d{7}@kiit\.ac\.in\b/);

  await page.getByRole('button', { name: 'View Demo Candidate 01' }).click();
  await expect(page.getByRole('dialog')).toContainText('Demo Candidate 01');
  await page.getByRole('button', { name: 'Open full technical dossier' }).click();
  await expect(page.getByRole('dialog')).toContainText('Demo Candidate 01');
  const dossier = await page.getByRole('dialog').innerText();
  expect(dossier).not.toMatch(/Ayush Roy|ayush-dev|2329027@kiit\.ac\.in/);
});

test('candidate intake presets use synthetic identities and reserved example URLs', async ({ page }) => {
  await page.goto('/workspace');
  await page.getByRole('button', { name: 'New Evaluation', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm & Calibrate Role Profile' }).click();

  await expect(page.getByText('Load Canonical Candidate Fixture')).toBeVisible();
  await expect(page.getByLabel('Candidate Full Name')).toHaveValue('Demo Candidate 01');
  await expect(page.getByLabel('Primary Email')).toHaveValue('candidate01@example.invalid');

  const rendered = await page.locator('body').innerText();
  expect(rendered).toContain('github.invalid');
  expect(rendered).not.toMatch(/Ayush Roy|Archi Srivastava|Atmaja Tripathy|Shreshth Nigam|P Ajay Kumar/);
  expect(rendered).not.toMatch(/github\.com\/(?:ayush-dev|erostova-web|mthorne-ai|tmansour-infra|soconnor-fullstack|pajaykumar-dev)/);
  expect(rendered).not.toContain('yorayriniwnl.in');
});
