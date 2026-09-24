import { expect, test } from '@playwright/test';

const syntheticCandidateId = 'd3333333-3333-4333-8333-333333333333';

test('production legacy entry routes lead to the synthetic demonstration', async ({ page }) => {
  for (const path of ['/', '/analyze', '/hr', '/workspace']) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/research-demo$/);
    await expect(page.getByRole('heading', { name: 'From evidence to interview.' })).toBeVisible();
  }
});

test('production live-analysis requests are blocked without reaching the backend', async ({ request }) => {
  for (const operation of ['intake', 'analyze']) {
    const response = await request.post(`/api/live/${operation}`, {
      data: { resume_text: 'must not reach the production backend' },
    });
    expect(response.status()).toBe(404);
    expect(response.headers()['cache-control']).toBe('no-store');
    expect(await response.json()).toEqual({ detail: 'Live analysis is disabled in this deployment.' });
  }
});

test('production synthetic run and rescore preserve explicit unknowns and fixed identity', async ({ page }) => {
  await page.goto('/research-demo');
  await expect(page.getByText(/generated synthetic observations/i)).toBeVisible();
  await expect(page.getByText(/no resumes or profiles are accepted/i)).toBeVisible();
  await expect(page.getByText(/no real person is assessed/i)).toBeVisible();
  await expect(page.getByText(/not a validated hiring predictor/i)).toBeVisible();
  await page.getByLabel('Evidence scenario').selectOption('empty');

  const runResponsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === '/api/demo' && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Run demonstration', exact: true }).click();
  const runResponse = await runResponsePromise;
  expect(runResponse.status()).toBe(200);
  const runRequest = runResponse.request().postDataJSON();
  expect(runRequest.operation).toBe('run');
  expect(Object.keys(runRequest.payload).sort()).toEqual([
    'excluded_sources', 'ownership_multiplier', 'reliability_false_positives', 'role', 'scenario',
  ]);
  const run = await runResponse.json();
  expect(run.dossier.candidate_id).toBe(syntheticCandidateId);
  expect(run.dossier.rci).toBeNull();
  expect(run.dossier.coverage).toBe(0);
  expect(run.graph.analysis_run_id).toBe(run.dossier.analysis_run_id);
  await expect(page.getByTestId('rci-value')).toHaveText('Unknown');
  await expect(page.getByTestId('coverage-value')).toHaveText('0.0%');

  await page.getByLabel('Override capability').selectOption('backend_engineering');
  const rescoreResponsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === '/api/demo' && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Apply focused override' }).click();
  const rescoreResponse = await rescoreResponsePromise;
  expect(rescoreResponse.status()).toBe(200);
  const rescoreRequest = rescoreResponse.request().postDataJSON();
  expect(rescoreRequest.operation).toBe('rescore');
  expect(Object.keys(rescoreRequest.payload).sort()).toEqual([
    'excluded_sources', 'ownership_multiplier', 'reliability_false_positives', 'role', 'scenario', 'weights',
  ]);
  expect(rescoreRequest.payload).not.toHaveProperty('run_id');
  const rescored = await rescoreResponse.json();
  expect(rescored.dossier.candidate_id).toBe(syntheticCandidateId);
  expect(rescored.dossier.rci).toBeNull();
  expect(rescored.dossier.coverage).toBe(0);
  expect(rescored.graph.analysis_run_id).toBe(rescored.dossier.analysis_run_id);
  expect(rescored.dossier.override_history.at(-1).justification)
    .toBe('Synthetic demonstration weight override');
  await expect(page.getByTestId('rci-value')).toHaveText('Unknown');
});
