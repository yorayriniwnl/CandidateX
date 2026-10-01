import { test, expect } from './fixtures';

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
    const memberOneRow = page.locator('tr:has-text("Demo Member One")');
    await expect(memberOneRow).toBeVisible();
    await expect(memberOneRow).toContainText('—');
    await expect(memberOneRow.getByRole('cell').nth(3)).toHaveText('Pending');

    // Verify another unevaluated sample candidate is also unscored
    const memberTwoRow = page.locator('tr:has-text("Demo Member Two")');
    await expect(memberTwoRow).toBeVisible();
    await expect(memberTwoRow).toContainText('—');
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

  test('Auditing a student from the HR page saves score, updates status, and avoids duplicate candidate rows', async ({ page }) => {
    // Start with offline roster (all 6 students available, unevaluated)
    await page.route('**/api/v1/candidates', route => route.abort());
    await page.route('**/api/v1/pipeline/run', route => route.fulfill({
      json: {
        analysis_run_id: 'test-run-001',
        candidate_id: '22222222-2222-2222-2222-222222222222',
        role: 'frontend',
        status: 'completed',
        rci: 86.4,
        coverage: 0.75,
        stages: [],
      }
    }));
    await page.goto('/hr');

    // Confirm initial 6 students
    await expect(page.locator('tbody tr')).toHaveCount(6);

    // Demo Member Two starts unevaluated and marked as Pending
    const memberTwoRow = page.locator('tr:has-text("Demo Member Two")');
    await expect(memberTwoRow).toBeVisible();
    await expect(memberTwoRow).toContainText('—');
    await expect(memberTwoRow).toContainText('Pending');

    // Click Audit on Demo Member Two
    const auditBtn = memberTwoRow.getByRole('button', { name: /audit archi srivastava/i });
    await auditBtn.click();

    // Verify modal is displayed
    const modal = page.locator('dialog');
    await expect(modal).toBeVisible();
    await expect(modal).toContainText('Audit Student: Demo Member Two');

    // Click Start Student Audit
    const startAuditBtn = modal.getByRole('button', { name: /start student audit/i });
    await startAuditBtn.click();

    // Wait for audit to complete
    await expect(modal).toContainText('Student Audit Successful', { timeout: 15000 });
    await expect(modal).toContainText('/ 100');

    // Close dialog
    const doneBtn = modal.getByRole('button', { name: /done/i });
    await doneBtn.click();
    await expect(modal).not.toBeVisible();

    // Verify Archi's row is updated with a score and completed status
    await expect(memberTwoRow).toContainText('/ 100');
    await expect(memberTwoRow).toContainText('Completed');

    // Verify candidate count is still exactly 6 (NO duplicate student row created!)
    await expect(page.locator('tbody tr')).toHaveCount(6);

    // Reload page to verify persistence from localStorage
    await page.reload();
    const memberTwoRowAfter = page.locator('tr:has-text("Demo Member Two")');
    await expect(memberTwoRowAfter).toBeVisible();
    await expect(memberTwoRowAfter).toContainText('/ 100');
    await expect(memberTwoRowAfter).toContainText('Completed');
    await expect(page.locator('tbody tr')).toHaveCount(6);
  });
});