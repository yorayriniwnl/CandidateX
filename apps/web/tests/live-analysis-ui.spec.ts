import { test, expect, type Page } from '@playwright/test';

const mockedIntake = {
  candidate_id: 'candidate-ui-test',
  manifest: {
    display_name: 'Example Candidate', email: null, claimed_skills: ['Python'], github_urls: [],
    linkedin_urls: [], coding_profile_urls: [], credential_urls: [], deployment_urls: [],
    portfolio_urls: [], project_links: [], project_claims: [],
  },
  filename: 'resume.pdf', document_sha256: 'a'.repeat(64), text_preview: 'Example Candidate\nSkills\nPython',
  warnings: [], storage: 'request_only',
  resume_review: { sections: {}, learning_skills: [], observations: [] },
};

const mockedAnalyze = {
  intake: mockedIntake,
  dossier: {
    evidence_mode: 'live', dossier_id: 'dossier-ui-test', candidate_id: 'candidate-ui-test',
    analysis_run_id: 'run-ui-test', role: 'backend', rci: null, coverage: 0,
    is_insufficient_evidence: true, evidence_records: [], capability_estimates: {
      backend_engineering: {
        capability_key: 'backend_engineering', estimate: null, is_observed: false,
        effective_evidence_count: 0, raw_evidence_count: 0, standard_error: 0, dispersion: 0,
        ci_lower: null, ci_upper: null, coverage_k: 0,
      },
    }, capability_conflicts: {}, role_requirements: [], ownership_assessments: [],
    claims_corroboration: [], interview_probes: [], interview_questions: [],
    system_limitations: [], versions: {}, generated_at: '2026-01-01T00:00:00Z',
  },
  sources: [], graph: { candidate_id: 'candidate-ui-test', analysis_run_id: 'run-ui-test', nodes: [], edges: [] },
  graph_snapshot: null, status: 'partial', analysis: {
    method: 'test', coverage: { supplied_sources: 0, observed_sources: 0, skills_declared: 1, skills_with_repository_matches: 0, credential_claims: 0 },
    role_fit: {
      requirement_matches: [], mandatory_total: 1, mandatory_observed: 0, mandatory_related: 0,
      mandatory_unknown: 1, mandatory_unresolved: 0, preferred_total: 0, preferred_observed: 0,
      preferred_related: 0, preferred_unknown: 0, preferred_unresolved: 0, critical_gaps: ['Python'],
    },
    skills: [], credentials: [], projects: [], education: [], experience: [], achievements: [],
    quantified_claims_to_verify: [], next_steps: [],
  },
};

async function mockLiveApi(page: Page) {
  await page.route('**/api/live/intake', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(mockedIntake),
  }));
  await page.route('**/api/live/analyze', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(mockedAnalyze),
  }));
}

test('first-run view makes the next action obvious without extra interpretation', async ({ page }) => {
  await page.setViewportSize({ width: 880, height: 900 });
  await page.goto('/analyze');
  await expect(page.getByRole('heading', { name: 'Upload a resume to begin' })).toBeVisible();
  await expect(page.getByText('Drop your resume here', { exact: true })).toBeVisible();
  await expect(page.getByText('Your review, in three moves', { exact: true })).toBeVisible();
  await expect(page.getByText('PDF or DOCX · up to 3 MB', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const uploadZone = await page.locator('label[for="resume-upload"]').boundingBox();
  expect((uploadZone?.y ?? Number.POSITIVE_INFINITY) + (uploadZone?.height ?? 0)).toBeLessThan(900);
});

test('keeps advanced source settings behind an intentional review step', async ({ page }) => {
  await mockLiveApi(page);
  await page.goto('/analyze');
  await expect(page.getByRole('heading', { name: 'Upload a resume to begin' })).toBeVisible();
  await expect(page.getByLabel('GitHub links to fetch')).toHaveCount(0);

  await page.locator('#resume-upload').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: Buffer.from('mock pdf') });
  await expect(page.getByText('Review public sources (optional)')).toBeVisible();
  await expect(page.getByLabel('GitHub links to fetch')).toBeHidden();

  await page.getByText('Review public sources (optional)').click();
  await expect(page.getByLabel('GitHub links to fetch')).toBeVisible();
});

test('leads with readable capability actions and keeps audit fields expandable', async ({ page }) => {
  await mockLiveApi(page);
  await page.goto('/analyze');
  await page.locator('#resume-upload').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: Buffer.from('mock pdf') });
  await page.getByRole('button', { name: 'Fetch live evidence & analyze' }).click();

  await expect(page.getByRole('heading', { name: 'What the evidence shows' })).toBeVisible();
  const table = page.getByRole('table', { name: 'Capability snapshot' });
  await expect(table.getByRole('columnheader', { name: 'Readiness' })).toBeVisible();
  await expect(table.getByRole('columnheader', { name: 'Next step' })).toBeVisible();
  await expect(page.getByText('Show audit details')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'What the job description is supported by' })).toBeVisible();
  await page.screenshot({ path: 'test-results/live-analysis-ui-result.png', fullPage: true });

  await page.getByText('Show audit details').click();
  await expect(page.getByRole('columnheader', { name: '95% interval' })).toBeVisible();
});
