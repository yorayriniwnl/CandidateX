import { test, expect } from './fixtures';
import { MOCK_DOSSIER } from '../data/mockDossier';

test('comparison starts empty and candidates can be selected and cleared with the keyboard', async ({ page }) => {
  await page.route('**/health', route => route.fulfill({ json: { status: 'ok' } }));
  await page.route('**/api/v1/candidates', route => route.fulfill({ json: [
    { id: 'keyboard-candidate', display_name: 'Keyboard Candidate', role: 'backend', has_completed_dossier: false },
  ] }));
  let releaseDossier!: () => void;
  let requestedDossier!: () => void;
  const dossierGate = new Promise<void>(resolve => { releaseDossier = resolve; });
  const dossierRequested = new Promise<void>(resolve => { requestedDossier = resolve; });
  await page.route('**/api/v1/dossier/keyboard-candidate', async route => {
    requestedDossier();
    await dossierGate;
    await route.fulfill({ json: { ...MOCK_DOSSIER, candidate_id: 'keyboard-candidate' } });
  });
  await page.goto('/workspace');
  await page.getByRole('button', { name: 'Compare Side by side', exact: true }).click();
  await expect(page.getByText('(0/3 selected)', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Download Matrix (.md)' })).toBeDisabled();
  const candidate = page.getByRole('button', { name: 'Keyboard Candidate (backend)', exact: true });
  await candidate.focus();
  await page.keyboard.press('Enter');
  await expect(candidate).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('(1/3 selected)', { exact: true })).toBeVisible();
  await dossierRequested;
  await page.keyboard.press('Space');
  await expect(candidate).toHaveAttribute('aria-pressed', 'false');
  await expect(page.getByText('(0/3 selected)', { exact: true })).toBeVisible();
  const response = page.waitForResponse('**/api/v1/dossier/keyboard-candidate');
  releaseDossier();
  await (await response).finished();
  // Let the response and React's resulting render settle before checking that
  // the cleared selection cannot be repopulated by the earlier request.
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(page.getByRole('button', { name: 'Print Comparison' })).toBeDisabled();
});

test('candidate drafts retain the selected role and dialogs restore keyboard focus', async ({ page }) => {
  await page.route('**/api/v1/candidates', route => route.fulfill({ json: [] }));
  await page.goto('/hr');
  const add = page.getByRole('button', { name: 'Add Candidate', exact: true }).first();
  await add.click();
  const dialog = page.getByRole('dialog', { name: 'Add Candidate', exact: true });
  await expect(dialog).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(add).toBeFocused();
  await add.click();
  await dialog.getByLabel('Full name').fill('Studio Test Candidate');
  await dialog.getByLabel('Hiring role').selectOption('frontend');
  await dialog.getByLabel(/Skills shared by the candidate/).fill('TypeScript');
  await dialog.getByLabel(/Skills shared by the candidate/).press('Enter');
  await dialog.getByRole('checkbox').check();
  await dialog.getByRole('button', { name: 'Add local draft' }).click();
  await expect(dialog).toHaveCount(0);
  await expect(add).toBeFocused();
  await page.reload();
  const row = page.getByRole('row').filter({ hasText: 'Studio Test Candidate' });
  await expect(row).toContainText('Frontend Developer');
  await expect(row).toContainText('Local draft');
  await row.getByRole('button', { name: 'View Studio Test Candidate' }).click();
  await expect(page.getByRole('dialog')).toContainText('TypeScript');
});

test('mobile navigation and workspace views remain usable at 320px', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 320, height: 844 });
  await page.goto('/workspace');
  const menu = page.getByRole('button', { name: 'Toggle navigation' });
  await menu.click();
  await expect(page.getByRole('navigation', { name: 'Primary navigation' }).getByRole('link', { name: 'Candidates', exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(menu).toHaveAttribute('aria-expanded', 'false');
  await expect(menu).toBeFocused();
  for (const [name, heading] of [
    ['Candidates Browse & search', 'Candidate Directory'],
    ['New Evaluation Run pipeline', 'Job Specification Intake'],
    ['Dossier Deep analysis', 'A person behind every profile.'],
    ['Compare Side by side', 'Candidate Comparative Capability Matrix'],
    ['Methodology Math & proofs', 'Prototype Methodology & Research Context'],
  ]) {
    await page.getByRole('button', { name, exact: true }).click();
    await expect(page.getByRole('button', { name, exact: true })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), name).toBe(true);
  }
});
