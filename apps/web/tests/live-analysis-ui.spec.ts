import { test, expect, type Page } from '@playwright/test';
import type { CEGNode } from '../types/cci';

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

const mockedLimitedAnalyze = {
  ...mockedAnalyze,
  sources: [{ url: 'https://github.com/example/api', status: 'observed', detail: 'Observed test receipt.' }],
  dossier: {
    ...mockedAnalyze.dossier,
    rci: 92,
    coverage: 0.2,
    capability_estimates: {
      ...mockedAnalyze.dossier.capability_estimates,
      backend_engineering: {
        ...mockedAnalyze.dossier.capability_estimates.backend_engineering,
        estimate: 92,
        is_observed: true,
        effective_evidence_count: 1,
        raw_evidence_count: 1,
        cluster_count: 1,
        ci_lower: null,
        ci_upper: null,
        coverage_k: 0.2,
      },
    },
    analysis_confidence: {
      evidence_strength: 'limited',
      explanation: 'Evidence strength is limited; one independent cluster and no interval are available.',
      uncertainty_flags: ['low_role_coverage', 'single_cluster', 'interval_unavailable'],
      role_coverage: 0.2,
      observed_capabilities: 1,
      independent_clusters: 1,
      capabilities_with_intervals: 0,
      interval_coverage: 0,
      maximum_interval_width: null,
      meaningful_conflicts: 0,
      mandatory_unknown: 0,
      mandatory_unresolved: 0,
      source_failures: 0,
      source_unscanned: 0,
      unusable_evidence_records: 0,
    },
  },
  source_health: {
    supplied_sources: 1,
    observed_sources: 1,
    failed_sources: 0,
    not_selected_sources: 0,
    not_scanned_sources: 0,
    blocked_sources: 0,
    is_partial: false,
    flags: [],
  },
};

const mockedStaleConfidenceAnalyze = {
  ...mockedLimitedAnalyze,
  sources: [
    { url: 'https://github.com/example/api', status: 'observed', detail: 'Observed test receipt.' },
    { url: 'https://example.invalid', status: 'timeout', detail: 'The source timed out.' },
  ],
  dossier: {
    ...mockedLimitedAnalyze.dossier,
    coverage: 0.9,
    capability_estimates: {
      ...mockedLimitedAnalyze.dossier.capability_estimates,
      backend_engineering: {
        ...mockedLimitedAnalyze.dossier.capability_estimates.backend_engineering,
        effective_evidence_count: 3,
        raw_evidence_count: 3,
        cluster_count: 3,
        ci_lower: 90,
        ci_upper: 94,
        coverage_k: 0.9,
      },
    },
    analysis_confidence: {
      ...mockedLimitedAnalyze.dossier.analysis_confidence,
      evidence_strength: 'well_supported',
      explanation: 'Evidence appears well supported.',
      uncertainty_flags: [],
      role_coverage: 0.9,
      independent_clusters: 3,
      capabilities_with_intervals: 1,
      interval_coverage: 1,
      maximum_interval_width: 4,
    },
  },
  source_health: {
    supplied_sources: 2,
    observed_sources: 1,
    failed_sources: 1,
    not_selected_sources: 0,
    not_scanned_sources: 0,
    blocked_sources: 0,
    is_partial: true,
    flags: ['source_failures'],
  },
};

const graphEvidence = {
  evidence_id: 'evidence-ui-3d', fingerprint: 'fingerprint-ui-3d', source_family: 'github',
  source_locator: 'https://github.com/example/api', immutable_revision: 'abc1234',
  target_capability: 'backend_engineering', support_score: 0.72, is_positive_support: true,
  confidence: 0.81, cluster_id: 'cluster-example-api', confidence_factors: { ownership_score: 0.4 },
  provenance: {
    artifact_path: 'app/main.py', raw_support_text: 'FastAPI route implementation observed.',
    extractor_version: 'test', verification_status: 'observed', observed_at: '2026-01-02T00:00:00Z',
  },
};

const mockedGraphAnalyze = {
  ...mockedAnalyze,
  sources: [{
    url: 'https://github.com/example/api', status: 'observed', detail: 'Inspected at immutable commit abc1234.',
    commit_sha: 'abc1234', fetched_at: '2026-01-02T00:00:00Z', files_inspected: 8, files_omitted: 0,
    evidence_count: 1, ownership_score: 0.4, kind: 'github_repository',
  }],
  status: 'completed',
  dossier: {
    ...mockedAnalyze.dossier,
    evidence_records: [graphEvidence],
    claims_corroboration: [{
      claim_id: 'claim-python-api', claim_text: 'Built and maintained a Python API.',
      target_capability: 'backend_engineering', status: 'partial', confidence: 0.72,
      grounding_evidence_ids: ['evidence-ui-3d'], citation_urls: ['https://github.com/example/api'],
      explanation: 'The inspected route is relevant to this claim; candidate attribution is not established.',
    }],
    interview_probes: [{
      capability_key: 'backend_engineering', rank: 1, priority_score: 0.81, role_weight: 0.3,
      coverage_gap_term: 0.4, uncertainty_term: 0.8, contradiction_term: 0,
    }],
    interview_questions: [{
      question_id: 'question-backend-1', target_capability: 'backend_engineering',
      question_text: 'Walk through the design choices behind the inspected API route.',
      rationale: 'The source shows a route implementation but does not establish the candidate’s role in it.',
      verification_guidance: 'Ask for trade-offs, failure handling, and a live code walkthrough.',
      grounding_evidence_ids: ['evidence-ui-3d'], suggested_followups: ['How would you test its failure paths?'],
    }],
    capability_estimates: {
      ...mockedAnalyze.dossier.capability_estimates,
      backend_engineering: {
        ...mockedAnalyze.dossier.capability_estimates.backend_engineering,
        estimate: 72, is_observed: true, effective_evidence_count: 0.8, raw_evidence_count: 1,
        cluster_count: 1, ci_lower: null, ci_upper: null, coverage_k: 0.3,
      },
    },
    role_weights: { backend_engineering: 0.3 },
  },
  analysis: {
    ...mockedAnalyze.analysis,
    skills: [{
      skill: 'Python', learning: false, status: 'partial', evidence: [{
        name: 'FastAPI', path: 'app/main.py', basis: 'source code', url: 'https://github.com/example/api', attribution_observed: false,
      }], evidence_count: 1, public_mentions: [],
      explanation: 'A Python route was observed in the inspected repository. Attribution and mastery remain unverified.',
    }],
  },
  graph: {
    candidate_id: 'candidate-ui-test', analysis_run_id: 'run-ui-test',
    nodes: [
      { id: 'candidate-ui-test', type: 'Candidate', label: 'Candidate', properties: { candidate_id: 'candidate-ui-test' } },
      { id: 'identity_candidate-ui-test', type: 'Identity', label: 'Supplied identity', properties: { candidate_id: 'candidate-ui-test', verification: 'not externally verified' } },
      { id: 'run-ui-test', type: 'AnalysisRun', label: 'Analysis snapshot', properties: { role: 'backend', evidence_mode: 'live' } },
      { id: 'source_github', type: 'Source', label: 'github', properties: { locator: 'https://github.com/example/api' } },
      { id: 'artifact_fingerprint-ui-3d', type: 'Artifact', label: 'app/main.py', properties: { artifact_path: 'app/main.py', revision: 'abc1234', fingerprint: 'fingerprint-ui-3d' } },
      { id: 'evidence-ui-3d', type: 'Evidence', label: 'github: backend_engineering', properties: { ...graphEvidence, score: 0.72 } },
      { id: 'cap_backend_engineering', type: 'Capability', label: 'backend_engineering', properties: { capability_key: 'backend_engineering', estimate: 72, is_observed: true } },
      { id: 'requirement_backend_engineering', type: 'RoleRequirement', label: 'backend: backend_engineering', properties: { weight: 0.3, jd_excerpts: [] } },
    ],
    edges: [
      { id: 'identity-candidate', source: 'identity_candidate-ui-test', target: 'candidate-ui-test', type: 'DERIVED_FROM', weight: 1, properties: {} },
      { id: 'run-candidate', source: 'run-ui-test', target: 'candidate-ui-test', type: 'DERIVED_FROM', weight: 1, properties: {} },
      { id: 'requirement-run', source: 'requirement_backend_engineering', target: 'run-ui-test', type: 'DERIVED_FROM', weight: 1, properties: {} },
      { id: 'capability-requirement', source: 'cap_backend_engineering', target: 'requirement_backend_engineering', type: 'CONTRIBUTES_TO', weight: 1, properties: {} },
      { id: 'artifact-source', source: 'artifact_fingerprint-ui-3d', target: 'source_github', type: 'CONTRIBUTES_TO', weight: 1, properties: {} },
      { id: 'artifact-identity', source: 'artifact_fingerprint-ui-3d', target: 'identity_candidate-ui-test', type: 'AUTHORED_BY', weight: 0.4, properties: {} },
      { id: 'evidence-artifact', source: 'evidence-ui-3d', target: 'artifact_fingerprint-ui-3d', type: 'DERIVED_FROM', weight: 1, properties: {} },
      { id: 'evidence-run', source: 'evidence-ui-3d', target: 'run-ui-test', type: 'CONTRIBUTES_TO', weight: 1, properties: {} },
      { id: 'evidence-capability', source: 'evidence-ui-3d', target: 'cap_backend_engineering', type: 'SUPPORTS_CAPABILITY', weight: 0.81, properties: {} },
    ],
  },
};

async function mockLiveApi(page: Page, analyzeBody: unknown = mockedAnalyze) {
  await page.route('**/api/live/intake', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(mockedIntake),
  }));
  await page.route('**/api/live/analyze', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(analyzeBody),
  }));
}

async function uploadResume(page: Page) {
  await page.locator('#resume-upload').setInputFiles({ name: 'resume.pdf', mimeType: 'application/pdf', buffer: Buffer.from('mock pdf') });
}

async function continueToAnalysis(page: Page) {
  await page.getByRole('button', { name: /Continue to target role/ }).click();
  await page.getByRole('button', { name: /Continue to public sources/ }).click();
  await page.getByRole('button', { name: /Continue to review/ }).click();
  await page.getByRole('button', { name: /Start live analysis/ }).click();
}

async function uploadAndAnalyze(page: Page) {
  await uploadResume(page);
  await continueToAnalysis(page);
}

test('first-run view makes the next action obvious without extra interpretation', async ({ page }) => {
  await page.setViewportSize({ width: 880, height: 900 });
  await page.goto('/analyze');
  await expect(page.getByRole('heading', { name: 'Build a candidate dossier.' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Start with the candidate’s document.' })).toBeVisible();
  await expect(page.getByText('Drop a resume here or browse', { exact: true })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Evaluation steps' }).getByRole('button', { name: /04 Review & analyze/ })).toBeDisabled();
  await expect(page.getByText('PDF or DOCX · up to 3 MB · digital text only', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/evidence-os-first-run.png', fullPage: true });
  const uploadZone = await page.locator('label[for="resume-upload"]').boundingBox();
  expect((uploadZone?.y ?? Number.POSITIVE_INFINITY) + (uploadZone?.height ?? 0)).toBeLessThan(900);
});

test('resume intake displays extracted declarations before source acquisition', async ({ page }) => {
  await mockLiveApi(page);
  await page.goto('/analyze');
  await uploadResume(page);
  await expect(page.getByRole('heading', { name: 'Example Candidate', exact: true })).toBeVisible();
  await expect(page.getByTestId('declared-skills')).toContainText('Python');
  await page.screenshot({ path: 'test-results/evidence-os-intake.png', fullPage: true });
});

test('shows the synchronous running state while the live request is pending', async ({ page }) => {
  await page.route('**/api/live/intake', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(mockedIntake),
  }));
  let releaseResponse!: () => void;
  const responseGate = new Promise<void>(resolve => { releaseResponse = resolve; });
  await page.route('**/api/live/analyze', async route => {
    await responseGate;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockedGraphAnalyze) });
  });

  try {
    await page.goto('/analyze');
    await uploadResume(page);
    await page.getByRole('button', { name: /Continue to target role/ }).click();
    await page.getByRole('button', { name: /Continue to public sources/ }).click();
    await page.getByRole('button', { name: /Continue to review/ }).click();
    await page.getByRole('button', { name: /Start live analysis/ }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Waiting for the live analysis response' })).toBeVisible();
    await page.screenshot({ path: 'test-results/evidence-os-running.png', fullPage: true });
  } finally {
    releaseResponse();
  }
  await expect(page.getByRole('region', { name: 'Live candidate dossier' })).toBeVisible();
});

test('shows the source manifest before acquisition and lets the reviewer choose what to fetch', async ({ page }) => {
  await mockLiveApi(page);
  await page.goto('/analyze');
  await uploadResume(page);
  await page.getByRole('button', { name: /Continue to target role/ }).click();
  await page.getByRole('button', { name: /Continue to public sources/ }).click();
  await expect(page.getByRole('heading', { name: 'Choose what to inspect.' })).toBeVisible();
  await expect(page.getByText('Nothing has been fetched yet.')).toBeVisible();
  await page.getByLabel('Add a public source URL').fill('https://github.com/example/api');
  await page.getByRole('button', { name: 'Add source' }).click();
  const selection = page.getByRole('checkbox', { name: /https:\/\/github.com\/example\/api/ });
  await expect(selection).toBeChecked();
  await selection.uncheck();
  await expect(page.getByText('0 public sources selected')).toBeVisible();
  await expect(page.getByRole('button', { name: /Continue to review/ })).toBeVisible();
});

test('leads with readable capability actions and keeps audit fields expandable', async ({ page }) => {
  await mockLiveApi(page, mockedGraphAnalyze);
  await page.goto('/analyze');
  await uploadAndAnalyze(page);

  await expect(page.getByText(/Neither is a hiring probability/i)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Evidence strength' })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Capability map' })).toBeVisible();
  const table = page.getByRole('table', { name: 'Role emphasis and observed evidence by capability' });
  await expect(table.getByRole('columnheader', { name: 'Estimate' })).toBeVisible();
  await expect(table.getByRole('columnheader', { name: '95% interval' })).toBeVisible();
  await expect(table.getByRole('columnheader', { name: 'Conflict' })).toBeVisible();
  await expect(page.getByText('Uncertainty and conflict diagnostics')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Skills and supporting evidence' })).toBeVisible();
  await page.screenshot({ path: 'test-results/evidence-os-result.png', fullPage: true });

  await page.getByText('Uncertainty and conflict diagnostics').click();
  await expect(page.getByText('Standard error', { exact: true })).toBeVisible();
});

test('shows returned score, coverage, and missing interval without inferred confidence', async ({ page }) => {
  await mockLiveApi(page, mockedLimitedAnalyze);
  await page.goto('/analyze');
  await uploadAndAnalyze(page);

  const row = page.getByRole('table', { name: 'Role emphasis and observed evidence by capability' }).getByRole('row').nth(1);
  await expect(row).toContainText('92.0');
  await expect(row).toContainText('20.0%');
  await expect(row).toContainText('Not returned');
  await expect(page.getByText(/Limited support|Limited evidence/)).toHaveCount(0);
});

test('shows returned source failure without inferring an evidence-strength status', async ({ page }) => {
  await mockLiveApi(page, mockedStaleConfidenceAnalyze);
  await page.goto('/analyze');
  await uploadAndAnalyze(page);

  await expect(page.getByText('The source timed out.')).toBeVisible();
  await expect(page.getByText(/Limited support|Limited evidence|Well supported/)).toHaveCount(0);
});

test('treats omitted legacy intervals as unavailable', async ({ page }) => {
  const legacy = JSON.parse(JSON.stringify(mockedStaleConfidenceAnalyze)) as any;
  delete legacy.dossier.capability_estimates.backend_engineering.ci_lower;
  delete legacy.dossier.capability_estimates.backend_engineering.ci_upper;
  legacy.source_health = {
    ...legacy.source_health,
    supplied_sources: 1,
    observed_sources: 1,
    failed_sources: 0,
    is_partial: false,
    flags: [],
  };
  legacy.sources = [legacy.sources[0]];

  await mockLiveApi(page, legacy);
  await page.goto('/analyze');
  await uploadAndAnalyze(page);

  await expect(page.getByText(/Limited support|Limited evidence/)).toHaveCount(0);
  const backendRow = page.getByRole('table', { name: 'Role emphasis and observed evidence by capability' }).getByRole('row').nth(1);
  await expect(backendRow).toContainText('Not returned');
});

test('loads the returned 3D evidence graph on demand and opens its matching evidence record', async ({ page }) => {
  await mockLiveApi(page, mockedGraphAnalyze);
  await page.goto('/analyze');
  await uploadAndAnalyze(page);

  const graph = page.getByRole('region', { name: 'Candidate evidence graph' });
  await expect(graph.getByText('8 nodes · 9 relationships')).toBeVisible();
  const nodeLegend = graph.getByRole('group', { name: 'Graph node semantics' });
  for (const label of ['Candidate', 'Source', 'Supporting evidence', 'Conflicting evidence', 'Unknown capability', 'Role requirement', 'Other graph node']) {
    await expect(nodeLegend.getByText(label, { exact: true })).toBeVisible();
  }
  const relationshipLegend = graph.getByRole('group', { name: 'Graph relationship semantics' });
  for (const label of ['Support', 'Contradiction', 'Interview question', 'Other relationship']) {
    await expect(relationshipLegend.getByText(label, { exact: true })).toBeVisible();
  }
  await expect(graph.locator('canvas')).toHaveCount(0);
  await graph.getByRole('button', { name: 'Load 3D evidence graph' }).click();
  await expect(graph.getByRole('img', { name: '3D evidence graph with 8 nodes and 9 relationships' })).toBeVisible();
  await expect(graph.getByText('Hover or select a node to reveal its label and returned details.')).toBeVisible();
  await graph.screenshot({ path: 'test-results/evidence-os-graph.png' });

  await graph.getByText('Text equivalent · nodes and relationships').click();
  await graph.getByRole('button', { name: /Inspect evidence node github: backend_engineering/ }).click();
  const provenance = page.getByRole('complementary', { name: 'Selected evidence provenance' });
  await expect(provenance).toBeVisible();
  await expect(provenance).toContainText('FastAPI route implementation observed.');
});

test('unknown CEG node types remain visible in 3D and in the searchable text equivalent', async ({ page }) => {
  await page.addInitScript(() => {
    const nativeGetContext = HTMLCanvasElement.prototype.getContext as unknown as (
      this: HTMLCanvasElement,
      type: string,
      options?: Record<string, unknown>,
    ) => RenderingContext | null;
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      configurable: true,
      value: function (this: HTMLCanvasElement, type: string, options?: Record<string, unknown>) {
        const attributes = type.startsWith('webgl') ? { ...options, preserveDrawingBuffer: true } : options;
        return nativeGetContext.call(this, type, attributes);
      },
    });
  });
  const analyzeWithUnknownNode = structuredClone(mockedGraphAnalyze);
  (analyzeWithUnknownNode.graph.nodes as CEGNode[]).push({
    id: 'signal_unclassified', type: 'ExternalSignal', label: 'Unclassified external signal',
    properties: { source_locator: 'https://example.test/signal', detail: 'Returned by a future CEG producer.' },
  });
  analyzeWithUnknownNode.graph.edges.push({
    id: 'signal_candidate', source: 'signal_unclassified', target: 'candidate-ui-test',
    type: 'REFERENCES', weight: 1, properties: {},
  });
  await mockLiveApi(page, analyzeWithUnknownNode);
  await page.goto('/analyze');
  await uploadAndAnalyze(page);

  const graph = page.getByRole('region', { name: 'Candidate evidence graph' });
  await graph.getByRole('button', { name: 'Load 3D evidence graph' }).click();
  const canvas = graph.getByRole('img', { name: '3D evidence graph with 9 nodes and 10 relationships' });
  await expect(canvas).toBeVisible();
  const litPixels = await canvas.evaluate(element => {
    const canvasElement = element as HTMLCanvasElement;
    const gl = canvasElement.getContext('webgl2') ?? canvasElement.getContext('webgl');
    if (!gl) return 0;
    gl.finish();
    const pixels = new Uint8Array(canvasElement.width * canvasElement.height * 4);
    gl.readPixels(0, 0, canvasElement.width, canvasElement.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    let lit = 0;
    for (let index = 0; index < pixels.length; index += 16) {
      if (pixels[index] + pixels[index + 1] + pixels[index + 2] > 48) lit += 1;
    }
    return lit;
  });
  expect(litPixels).toBeGreaterThan(10);
  await graph.screenshot({ path: 'test-results/evidence-graph-unknown-types.png' });

  await graph.getByText('Text equivalent · nodes and relationships').click();
  const unknownNode = graph.getByRole('button', { name: /Inspect external signal node Unclassified external signal/ });
  await expect(unknownNode).toBeVisible();
  await unknownNode.click();
  await expect(graph.getByRole('complementary', { name: 'Selected text graph node details' }))
    .toContainText('Returned by a future CEG producer.');
  await page.setViewportSize({ width: 390, height: 844 });
  await graph.scrollIntoViewIfNeeded();
  await canvas.screenshot({ path: 'test-results/evidence-graph-mobile.png' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('shows the searchable text equivalent when a WebGL context is lost', async ({ page }) => {
  await mockLiveApi(page, mockedGraphAnalyze);
  await page.goto('/analyze');
  await uploadAndAnalyze(page);

  const graph = page.getByRole('region', { name: 'Candidate evidence graph' });
  await graph.getByRole('button', { name: 'Load 3D evidence graph' }).click();
  const canvas = graph.getByRole('img', { name: '3D evidence graph with 8 nodes and 9 relationships' });
  await expect(canvas).toBeVisible();
  await canvas.evaluate(element => element.dispatchEvent(new Event('webglcontextlost', { cancelable: true })));
  await expect(graph.getByRole('status')).toContainText('3D rendering is unavailable in this browser.');
  await expect(graph.getByRole('button', { name: 'Reset view' })).toBeDisabled();
  await graph.getByText('Text equivalent · nodes and relationships').click();
  await expect(graph.getByLabel('Find a node')).toBeVisible();
  await expect(graph.getByRole('button', { name: /Inspect evidence node github: backend_engineering/ })).toBeVisible();
});

test('opens a traceable dossier rail across capabilities, claims, sources, gaps, interview, graph, and audit', async ({ page }) => {
  await mockLiveApi(page, mockedGraphAnalyze);
  await page.goto('/analyze');
  await uploadAndAnalyze(page);

  const dossier = page.getByRole('region', { name: 'Live candidate dossier' });
  const navigation = dossier.getByRole('navigation', { name: 'Dossier sections' });
  for (const section of ['overview', 'capabilities', 'evidence', 'claims', 'sources', 'conflicts', 'interview', 'evidence-graph', 'audit']) {
    await expect(navigation.locator(`a[href="#${section}"]`)).toBeVisible();
  }
  await expect(dossier.getByRole('heading', { name: 'Candidate evidence graph' })).toBeVisible();
  await expect(dossier.getByRole('heading', { name: 'Claims and corroboration' })).toBeVisible();
  await expect(dossier.getByRole('heading', { name: 'Source coverage' })).toBeVisible();
  await expect(dossier.getByRole('heading', { name: 'Unknowns and conflicts' })).toBeVisible();
  await expect(dossier.getByRole('heading', { name: 'Interview plan' })).toBeVisible();
  await expect(dossier.getByRole('heading', { name: 'Audit and limitations' })).toBeVisible();
  await page.locator('#capabilities').screenshot({ path: 'test-results/evidence-os-capability.png' });
  await page.locator('#evidence').screenshot({ path: 'test-results/evidence-os-ledger.png' });
  await page.locator('#sources').screenshot({ path: 'test-results/evidence-os-receipt.png' });
  await page.locator('#interview').screenshot({ path: 'test-results/evidence-os-interview.png' });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(dossier.getByText('Swipe or scroll to see all dossier sections')).toBeVisible();
  await expect(navigation).toHaveAttribute('aria-describedby', 'dossier-section-nav-description');
  await navigation.evaluate(element => { element.scrollLeft = element.scrollWidth; });
  expect(await navigation.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  await expect(navigation.locator('a[href="#audit"]')).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/evidence-os-mobile.png' });
});
