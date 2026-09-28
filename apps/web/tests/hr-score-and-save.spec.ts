import { test, expect } from '@playwright/test';

test.describe('HR Tab and Candidate Review Profile Saving', () => {
  test('HR dashboard renders the Score column and leaves unevaluated roster candidates unscored', async ({ page }) => {
    await page.goto('/hr');

    // Verify Score column header exists in the table
    const tableHeader = page.locator('.studio-table-head');
    await expect(tableHeader).toContainText('Candidate');
    await expect(tableHeader).toContainText('Role');
    await expect(tableHeader).toContainText('Score');
    await expect(tableHeader).toContainText('Evaluation');
    await expect(tableHeader).toContainText('Evidence');
    await expect(tableHeader).toContainText('Alerts');
    await expect(tableHeader).toContainText('Action');

    // Roster entries are identity/role fixtures only. They stay unscored until
    // an actual dossier is saved or returned by the backend.
    const ayushRow = page.locator('tr:has-text("Ayush Roy")');
    await expect(ayushRow).toBeVisible();
    await expect(ayushRow).toContainText('—');
    await expect(ayushRow).toContainText('Not completed');

    // Verify another unevaluated sample candidate is also unscored
    const archiRow = page.locator('tr:has-text("Archi Srivastava")');
    await expect(archiRow).toBeVisible();
    await expect(archiRow).toContainText('—');
  });

  test('Saved review candidate profile appears in HR tab with Score and details', async ({ page }) => {
    // Inject a candidate profile saved from a completed review into localStorage
    await page.goto('/hr');
    await page.evaluate(() => {
      const reviewedCandidate = {
        id: 'rev-candidate-test-01',
        display_name: 'Test Review Candidate',
        primary_email: 'test.review@candidatex.dev',
        role: 'backend',
        has_completed_dossier: true,
        rci: 88.5,
        coverage: 0.85,
        has_meaningful_conflict: false,
        created_at: new Date().toISOString(),
        source: 'live',
        manifest: {
          candidate_id: 'rev-candidate-test-01',
          full_name: 'Test Review Candidate',
          primary_email: 'test.review@candidatex.dev',
          github_usernames: ['testreview'],
          github_repositories: ['https://github.com/testreview/engine'],
          deployment_urls: [],
          portfolio_urls: [],
          declared_skills: ['Go', 'Distributed Systems', 'PostgreSQL'],
          extraction_metadata: { source: 'live_review', role: 'backend' },
        },
      };
      localStorage.setItem('cci_hr_saved_candidates', JSON.stringify([reviewedCandidate]));
    });

    // Reload page to verify saved candidate is listed in HR
    await page.reload();

    const candidateRow = page.locator('tr:has-text("Test Review Candidate")');
    await expect(candidateRow).toBeVisible();
    await expect(candidateRow).toContainText('Backend Developer');
    await expect(candidateRow).toContainText('88.5');
    await expect(candidateRow).toContainText('/ 100');
    await expect(candidateRow).toContainText('Completed');

    // Click View to open CandidateQuickView
    const viewButton = candidateRow.getByRole('button', { name: /view test review candidate/i });
    await viewButton.click();

    // Verify modal displays candidate and score in subtitle and summary card
    const modal = page.locator('dialog');
    await expect(modal).toBeVisible();
    await expect(modal).toContainText('Test Review Candidate');
    await expect(modal).toContainText('Score: 88.5 / 100');

    // Close modal
    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible();
  });

  test('Sorting candidates by Score works interactively', async ({ page }) => {
    await page.goto('/hr');
    await page.evaluate(() => {
      const candidates = [
        {
          id: 'cand-low',
          display_name: 'Low Score Candidate',
          role: 'frontend',
          has_completed_dossier: true,
          rci: 65.0,
          created_at: new Date().toISOString(),
          source: 'live',
        },
        {
          id: 'cand-high',
          display_name: 'High Score Candidate',
          role: 'backend',
          has_completed_dossier: true,
          rci: 94.2,
          created_at: new Date().toISOString(),
          source: 'live',
        },
      ];
      localStorage.setItem('cci_hr_saved_candidates', JSON.stringify(candidates));
    });

    await page.reload();
    await expect(page.locator('table')).toBeVisible({ timeout: 10000 });

    const scoreSortBtn = page.locator('thead button:has-text("Score")');
    await expect(scoreSortBtn).toBeVisible();

    // Click to sort by Score descending
    await scoreSortBtn.click();

    // High Score Candidate (94.2) should appear before Low Score Candidate (65.0)
    const rows = page.locator('tbody tr');
    const firstRowText = await rows.first().textContent();
    expect(firstRowText).toContain('High Score Candidate');
    expect(firstRowText).toContain('94.2');

    // Click again to sort by Score ascending
    await scoreSortBtn.click();
    const rowsAsc = page.locator('tbody tr');
    const firstRowAscText = await rowsAsc.first().textContent();
    // Candidates with no score (— / -1) come first when ascending
    expect(firstRowAscText).toContain('—');
  });
});

