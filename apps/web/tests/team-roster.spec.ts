import { test, expect, type Page } from './fixtures';

const members = [
  { id: '11111111-1111-1111-1111-111111111111', name: 'Demo Member One', email: 'member1@example.test', role: 'fullstack', label: 'Fullstack, SDE' },
  { id: '22222222-2222-2222-2222-222222222222', name: 'Demo Member Two', email: 'member2@example.test', role: 'frontend', label: 'Frontend' },
  { id: '33333333-3333-3333-3333-333333333333', name: 'Demo Member Three', email: 'member3@example.test', role: 'ml_engineer', label: 'ML Engineer' },
  { id: '44444444-4444-4444-4444-444444444444', name: 'Demo Member Four', email: 'member4@example.test', role: 'devops_cloud', label: 'DevOps' },
  { id: '55555555-5555-5555-5555-555555555555', name: 'Shreshth Nigam', email: '2329064@kiit.ac.in', role: 'devops_cloud', label: 'SRE' },
  { id: '77777777-7777-7777-7777-777777777777', name: 'P Ajay Kumar', email: '2329195@kiit.ac.in', role: 'backend', label: 'Backend' },
];

async function expectRoster(page: Page, count = 6, forceAssessed?: boolean) {
  await expect(page.locator('tbody tr')).toHaveCount(count);
  for (const member of members) {
    const row = page.getByRole('row').filter({ hasText: member.email });
    await expect(row).toHaveCount(1);
    await expect(row.getByRole('rowheader')).toContainText(member.name);
    if (forceAssessed === true) {
      await expect(row.getByRole('cell').first()).toHaveText(member.label);
    } else if (forceAssessed === false) {
      await expect(row.getByRole('cell').first()).toHaveText('—');
    } else {
      await expect(row.getByRole('cell').first()).toHaveText(new RegExp(`^(?:${member.label.replace('+', '\\+')}|—|-)$`));
    }
    await expect(row.getByRole('link', { name: member.email })).toHaveAttribute('href', `mailto:${member.email}`);
  }
}

test('all six members remain available offline with their roles and email links', async ({ page }, testInfo) => {
  await page.route('**/api/v1/candidates', route => route.abort());
  await page.goto('/hr');
  await expectRoster(page, 6, false);
  await expect(page.locator('tbody')).not.toContainText('/ 100');
  await page.screenshot({ path: testInfo.outputPath('hiring-dashboard.png'), fullPage: true });

  await page.getByRole('button', { name: 'View Shreshth Nigam', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('SRE');
  await page.keyboard.press('Escape');

  await page.getByLabel('Role', { exact: true }).selectOption('fullstack');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await expect(page.locator('tbody')).toContainText('Demo Member One');
  await page.getByLabel('Role', { exact: true }).selectOption('devops_cloud');
  await expect(page.locator('tbody tr')).toHaveCount(2);
  await expect(page.locator('tbody')).toContainText('Demo Member Four');
  await expect(page.locator('tbody')).toContainText('Shreshth Nigam');
  await page.getByRole('button', { name: 'Clear filters', exact: true }).click();
  await page.getByLabel('Search candidate').fill('2329195@kiit.ac.in');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await expect(page.locator('tbody')).toContainText('P Ajay Kumar');
});

test('live team records replace samples by ID or email and retain scores', async ({ page }) => {
  await page.route('**/api/v1/candidates', route => route.fulfill({ json: [
    ...members.map((member, index) => ({
      id: index === 1 ? 'legacy-archi-id' : member.id,
      display_name: index === 5 ? 'P Ajay Kumar (Contradictory / Discrepancy)' : member.name,
      primary_email: member.email.toUpperCase(),
      role: index === 0 ? 'backend' : index === 4 ? 'fullstack' : member.role,
      has_completed_dossier: true,
      has_meaningful_conflict: false,
      rci: 70 + index,
      created_at: '',
    })),
    { id: 'other-candidate', display_name: 'Another Candidate', role: 'backend', has_completed_dossier: false },
  ] }));
  await page.goto('/hr');
  await expectRoster(page, 7);
  for (const [index, member] of members.entries()) {
    await expect(page.getByRole('row').filter({ hasText: member.email })).toContainText(`${70 + index}.0`);
  }
  await page.getByRole('button', { name: 'Refresh list', exact: true }).click();
  await expectRoster(page, 7);
});

test('a locally saved review replaces a matching live member with a different ID', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('cci_hr_saved_candidates', JSON.stringify([{
    id: 'saved-ayush-review', display_name: 'Demo Member One', primary_email: ' 2329027@KIIT.AC.IN ',
    role: 'backend', has_completed_dossier: true, has_meaningful_conflict: false,
    rci: 94.2, observed_capabilities: 8, source: 'live', created_at: '',
  }])));
  await page.route('**/api/v1/candidates', route => route.fulfill({ json: [{
    id: members[0].id, display_name: members[0].name, primary_email: members[0].email,
    role: 'backend', has_completed_dossier: true, has_meaningful_conflict: false, rci: 70,
  }] }));
  await page.goto('/hr');
  await expectRoster(page);
  const row = page.getByRole('row').filter({ hasText: members[0].email });
  await expect(row).toContainText('94.2');
  await expect(row.getByRole('cell').nth(2)).toHaveText(/8\s*\/\s*12/);
});

test('directory, comparison, and intake keep the same six members with a partial API roster', async ({ page }) => {
  await page.route('**/health', route => route.fulfill({ json: { status: 'ok' } }));
  await page.route('**/api/v1/candidates', route => route.fulfill({ json: [{
    id: members[0].id, display_name: members[0].name, primary_email: members[0].email,
    role: 'backend', has_completed_dossier: false, has_meaningful_conflict: false,
  }] }));
  await page.goto('/workspace');
  for (const member of members) {
    await expect(page.getByRole('heading', { name: member.name, exact: true })).toBeVisible();
    await expect(page.getByText(member.email, { exact: true })).toHaveCount(1);
    await expect(page.getByText(member.label, { exact: true }).filter({ visible: true })).toHaveCount(0);
  }
  await page.getByRole('button', { name: 'Table View', exact: true }).click();
  await expect(page.locator('tbody tr')).toHaveCount(6);
  for (const member of members) {
    const row = page.getByRole('row').filter({ hasText: member.email });
    await expect(row).toHaveCount(1);
    await expect(row).toContainText('UNKNOWN');
    await expect(row).toContainText('Not evaluated');
  }
  await page.getByRole('button', { name: 'Compare Side by side', exact: true }).click();
  for (const member of members) {
    await expect(page.getByRole('button', { name: `${member.name} (${member.label})`, exact: true })).toBeVisible();
  }

  await page.getByRole('button', { name: 'New Evaluation Run pipeline', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm role profile', exact: true }).click();
  for (const member of members) {
    const preset = page.locator('.cursor-pointer').filter({ has: page.getByText(member.label, { exact: true }) }).filter({ has: page.getByText(member.name, { exact: true }) });
    await preset.click();
    await expect(page.getByLabel('Candidate Full Name')).toHaveValue(member.name);
    await expect(page.getByLabel('Primary Email')).toHaveValue(member.email);
  }
});
