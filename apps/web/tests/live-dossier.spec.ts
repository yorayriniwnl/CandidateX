import { test, expect } from '@playwright/test';
import { createLiveResult, fixtureIntake, FIXTURE_REPOSITORY } from './fixtures/live-result';

const fixturePdf = Buffer.from('%PDF-1.4 test-only intake fixture');

async function alignSectionBelowHeader(page: import('@playwright/test').Page, selector: string) {
  await page.locator(selector).first().evaluate(element => {
    const target = window.scrollY + element.getBoundingClientRect().top - 88;
    window.scrollTo(0, Math.max(0, target));
  });
}

test('contract-backed partial dossier supports provenance drilldown, filters, graph, audit, and visual states', async ({ page }) => {
  const consoleErrors: string[] = [];
  const failedResponses: string[] = [];
  await page.emulateMedia({ reducedMotion: 'reduce' });
  let submitted: { intake: typeof fixtureIntake; role: string; jd_text: string; github_urls: string[]; external_urls: string[] } | null = null;
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  page.on('pageerror', error => consoleErrors.push(error.message));
  page.on('response', response => { if (response.status() >= 500) failedResponses.push(`${response.status()} ${response.url()}`); });

  await page.route('**/api/live/intake', route => route.fulfill({ status: 200, json: fixtureIntake }));
  await page.route('**/api/live/analyze', async route => {
    submitted = route.request().postDataJSON();
    await new Promise(resolve => setTimeout(resolve, 2000));
    await route.fulfill({ status: 200, json: createLiveResult(submitted!.intake) });
  });

  await page.goto('/analyze');
  await page.locator('#resume-upload').setInputFiles({ name: 'fixture-resume.pdf', mimeType: 'application/pdf', buffer: fixturePdf });
  await expect(page.getByRole('heading', { name: 'Fixture Candidate' })).toBeVisible();
  await page.getByRole('button', { name: 'Continue to target role' }).click();
  await page.getByLabel('Job description').fill('Build reliable APIs with PostgreSQL, deployment automation, and security tests.');
  await page.getByRole('button', { name: 'Continue to public sources' }).click();
  await expect(page.getByRole('heading', { name: 'Choose what to inspect.' })).toBeVisible();
  await expect(page.getByRole('checkbox', { name: new RegExp(FIXTURE_REPOSITORY.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) })).toBeChecked();
  await page.getByLabel('Add a public source URL').fill('javascript:alert(1)');
  await page.getByRole('button', { name: 'Add source' }).click();
  await expect(page.getByRole('region', { name: 'Choose what to inspect.' }).getByRole('alert')).toContainText('Only credential-free HTTP or HTTPS URLs can be submitted.');
  await expect(page.getByRole('checkbox', { name: 'javascript:alert(1) (Unsupported URL)' })).toBeDisabled();
  await page.getByRole('button', { name: 'Continue to review' }).click();
  await expect(page.getByRole('heading', { name: 'Review analysis' })).toBeVisible();
  await page.getByRole('button', { name: 'Start live analysis' }).click();

  await expect(page.getByText('Waiting for the live analysis response')).toBeVisible();
  await expect(page.getByTestId('pending-analysis-skeleton')).toBeVisible();
  await expect(page.getByTestId('pending-analysis-skeleton').locator('span').first()).toHaveCSS('animation-name', 'none');
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(page.getByTestId('pending-analysis-skeleton')).toBeInViewport();
  await page.screenshot({ path: 'test-results/analysis-running-state.png' });

  await expect(page.getByRole('heading', { name: 'Fixture Candidate', exact: true })).toBeVisible();
  await expect(page.getByText('Analysis completed with gaps')).toBeVisible();
  await expect(page.getByTestId('source-receipts-count')).toHaveText('5');
  await expect(page.getByTestId('repositories-inspected-count')).toHaveText('1');
  await expect(page.locator('#overview')).toContainText('74.6');
  await expect(page.locator('#overview')).toContainText('67.0%');
  await expect(page.locator('#overview')).toContainText('SOURCES RETURNED');
  await alignSectionBelowHeader(page, '#overview');
  await page.locator('#overview').screenshot({ path: 'test-results/result-overview.png' });

  expect(submitted).not.toBeNull();
  expect(submitted!.role).toBe('backend');
  expect(submitted!.jd_text).toContain('deployment automation');
  expect(submitted!.github_urls).toContain(FIXTURE_REPOSITORY);
  expect(submitted!.external_urls).toContain('https://www.linkedin.com/in/fixture-candidate');
  expect(submitted!.external_urls).not.toContain('javascript:alert(1)');

  await page.getByRole('button', { name: 'Backend Engineering' }).first().click();
  await expect(page.getByRole('heading', { name: 'Backend Engineering' }).last()).toBeVisible();
  await expect(page.getByRole('meter', { name: 'Backend Engineering role weight' })).toHaveAttribute('aria-valuenow', '28');
  await alignSectionBelowHeader(page, '#capabilities');
  await page.locator('#capabilities').screenshot({ path: 'test-results/capability-inspector.png' });
  await page.getByRole('button', { name: /Inspect all 1 evidence record/ }).click();
  await expect(page.getByLabel('Filter by capability')).toHaveValue('backend_engineering');
  await expect(page.getByRole('complementary', { name: 'Selected evidence provenance' })).toContainText('FastAPI routes validate request data');
  await page.getByLabel('Filter by capability').selectOption('all');
  await expect(page.getByText(/of 3 matching records/)).toBeVisible();
  await alignSectionBelowHeader(page, '#evidence');
  await page.locator('#evidence').screenshot({ path: 'test-results/evidence-ledger.png' });

  await page.getByLabel('Repository', { exact: true }).selectOption(FIXTURE_REPOSITORY);
  await page.getByLabel('Confidence minimum (0 to 1)').fill('0.8');
  await page.getByLabel('Observed after').fill('2026-09-20');
  await expect(page.getByText('1 matching record', { exact: false })).toBeVisible();
  await page.getByLabel('Support direction').selectOption('negative');
  await expect(page.getByText('No evidence records match these filters.')).toBeVisible();
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await expect(page.getByText(/of 3 matching records/)).toBeVisible();
  await page.getByRole('button', { name: /Sort by Confidence/ }).click();
  await expect(page.getByRole('columnheader', { name: 'Sort by Confidence' })).toHaveAttribute('aria-sort', 'ascending');
  await page.getByRole('button', { name: /base image tag is unpinned/ }).click();
  await expect(page.getByRole('complementary', { name: 'Selected evidence provenance' })).toContainText('contradicting observation');

  await page.locator('#claims').scrollIntoViewIfNeeded();
  await expect(page.locator('#claims')).toContainText('self-reported');
  await expect(page.locator('#claims')).toContainText('public text mention');
  await expect(page.locator('#claims')).toContainText('does not authenticate');

  await page.locator('#sources').scrollIntoViewIfNeeded();
  await expect(page.locator('#sources')).toContainText('access restricted');
  await expect(page.locator('#sources')).toContainText('not scanned');
  await page.getByText('Repository intelligence · inspected files only').click();
  await expect(page.locator('#sources')).toContainText('Open issues');
  await expect(page.locator('#sources')).toContainText('Last push');
  await expect(page.locator('#sources')).toContainText('File categories by inspected file');
  await expect(page.locator('#sources')).toContainText('configuration');
  await expect(page.locator('#sources')).toContainText('Only five files were inspected');
  await page.setViewportSize({ width: 1280, height: 1000 });
  await alignSectionBelowHeader(page, '#sources article');
  await page.screenshot({ path: 'test-results/source-receipt.png' });

  await page.locator('#conflicts').scrollIntoViewIfNeeded();
  await expect(page.locator('#conflicts')).toContainText('Meaningful contradictions');
  await expect(page.locator('#conflicts')).toContainText('The base image tag is unpinned');
  await page.locator('#interview').scrollIntoViewIfNeeded();
  await expect(page.locator('#interview')).toContainText('How would you pin and update a production container base image?');
  await page.getByLabel(/Interviewer notes/).first().fill('Ask about digest pinning.');
  await alignSectionBelowHeader(page, '#interview');
  await page.locator('#interview').screenshot({ path: 'test-results/interview-plan.png' });

  const graph = page.locator('#evidence-graph');
  await graph.scrollIntoViewIfNeeded();
  await graph.getByRole('button', { name: 'Load 3D evidence graph' }).click();
  await expect(graph.getByRole('img', { name: /3D evidence graph with/ })).toBeVisible();
  await alignSectionBelowHeader(page, '#evidence-graph');
  await graph.screenshot({ path: 'test-results/evidence-graph.png' });
  await graph.getByText('Text equivalent · nodes and relationships').click();
  await expect(graph.getByLabel('Find a node')).toBeVisible();
  const evidenceNode = graph.getByRole('button', { name: /Inspect evidence node FastAPI route architecture/ });
  await evidenceNode.focus();
  await evidenceNode.press('Enter');
  await expect(page.getByRole('complementary', { name: 'Selected evidence provenance' })).toContainText('FastAPI routes validate request data');
  await page.locator('#audit').scrollIntoViewIfNeeded();
  await expect(page.locator('#audit')).toContainText('static_analyzer');

  expect(consoleErrors).toEqual([]);
  expect(failedResponses).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: 'test-results/result-mobile-viewport.png' });
  await page.screenshot({ path: 'test-results/result-mobile.png', fullPage: true });
});

test('large job descriptions remain bounded and visible at the 20,000-character limit', async ({ page }) => {
  await page.route('**/api/live/intake', route => route.fulfill({ status: 200, json: fixtureIntake }));
  await page.goto('/analyze');
  await page.locator('#resume-upload').setInputFiles({ name: 'fixture-resume.pdf', mimeType: 'application/pdf', buffer: fixturePdf });
  await page.getByRole('button', { name: 'Continue to target role' }).click();
  await page.getByLabel('Job description').fill('x'.repeat(20000));
  await expect(page.getByText('20,000 / 20,000 characters')).toBeVisible();
  await page.getByRole('button', { name: 'Continue to public sources' }).click();
  await page.getByRole('button', { name: 'Continue to review' }).click();
  await expect(page.getByText('JOB DESCRIPTION PREVIEW')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
