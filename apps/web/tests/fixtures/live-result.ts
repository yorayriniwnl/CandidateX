import type { CapabilityKey } from '../../types/cci';
import type { LiveResult, ResumeIntake } from '../../lib/live-analysis';

export const FIXTURE_REPOSITORY = 'https://github.com/fixture-candidate/api-service';
export const FIXTURE_SECOND_REPOSITORY = 'https://github.com/fixture-candidate/data-toolkit';

export const fixtureIntake: ResumeIntake = {
  candidate_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  manifest: {
    display_name: 'Fixture Candidate',
    email: 'fixture@example.test',
    claimed_skills: ['Python', 'FastAPI', 'Docker'],
    github_urls: [FIXTURE_REPOSITORY, FIXTURE_SECOND_REPOSITORY],
    linkedin_urls: ['https://www.linkedin.com/in/fixture-candidate'],
    coding_profile_urls: [],
    credential_urls: ['https://example.com/credentials/cloud-foundations'],
    deployment_urls: [],
    portfolio_urls: ['https://fixture-candidate.example.com'],
    project_links: [FIXTURE_REPOSITORY],
    project_claims: [{ title: 'API Service', description: 'A resume-declared API project.', technologies: ['Python', 'FastAPI'] }],
  },
  filename: 'fixture-resume.pdf',
  document_sha256: 'b'.repeat(64),
  text_preview: 'Fixture Candidate\nSoftware Engineer\nSkills\nPython, FastAPI, Docker',
  warnings: [],
  storage: 'request_scoped',
  resume_review: {
    sections: { skills: ['Python, FastAPI, Docker'], projects: ['API Service'] },
    learning_skills: [],
    observations: ['Resume identity and skills are self-reported.'],
  },
};

const CAPABILITIES: CapabilityKey[] = [
  'backend_engineering', 'frontend_engineering', 'database_engineering', 'devops_cloud',
  'machine_learning', 'data_engineering', 'algorithms_problem_solving', 'testing_quality',
  'security', 'software_architecture', 'collaboration', 'documentation_communication',
];

const CAPABILITY_WEIGHTS: Record<CapabilityKey, number> = {
  backend_engineering: 0.28,
  frontend_engineering: 0.06,
  database_engineering: 0.18,
  devops_cloud: 0.04,
  machine_learning: 0.02,
  data_engineering: 0.02,
  algorithms_problem_solving: 0.02,
  testing_quality: 0.12,
  security: 0.12,
  software_architecture: 0.12,
  collaboration: 0.01,
  documentation_communication: 0.01,
};

const evidenceIds = {
  api: '10000000-0000-4000-8000-000000000001',
  container: '10000000-0000-4000-8000-000000000002',
  security: '10000000-0000-4000-8000-000000000003',
};

function evidenceRecords(): LiveResult['dossier']['evidence_records'] {
  return [
    {
      evidence_id: evidenceIds.api,
      fingerprint: 'e'.repeat(64),
      source_family: 'github',
      source_locator: FIXTURE_REPOSITORY,
      immutable_revision: 'a1b2c3d4e5f67890',
      target_capability: 'backend_engineering',
      support_score: 84.1,
      is_positive_support: true,
      confidence: 0.86,
      cluster_id: 'api-routes',
      confidence_factors: {
        ownership_score: 0.72,
        recency_factor: 0.91,
        source_reliability: 0.88,
        artifact_integrity: 1,
      },
      provenance: {
        artifact_path: 'app/main.py',
        raw_support_text: 'FastAPI routes validate request data and return typed responses.',
        extractor_version: 'static-analyzer/2.1',
        verification_status: 'supporting observation',
        observed_at: '2026-09-22T09:15:00Z',
        artifact_url: `${FIXTURE_REPOSITORY}/blob/a1b2c3d4e5f67890/app/main.py`,
        artifact_sha256: '1'.repeat(64),
        symbol_or_line: 'create_app · lines 18–42',
      },
    },
    {
      evidence_id: evidenceIds.container,
      fingerprint: 'f'.repeat(64),
      source_family: 'github',
      source_locator: FIXTURE_REPOSITORY,
      immutable_revision: 'a1b2c3d4e5f67890',
      target_capability: 'security',
      support_score: 34.5,
      is_positive_support: false,
      confidence: 0.56,
      cluster_id: 'container-config',
      confidence_factors: {
        ownership_score: 0.72,
        recency_factor: 0.74,
        source_reliability: 0.88,
        artifact_integrity: 1,
      },
      provenance: {
        artifact_path: 'Dockerfile',
        raw_support_text: 'The base image tag is unpinned, which limits reproducibility.',
        extractor_version: 'static-analyzer/2.1',
        verification_status: 'contradicting observation',
        observed_at: '2026-09-18T14:20:00Z',
        artifact_url: `${FIXTURE_REPOSITORY}/blob/a1b2c3d4e5f67890/Dockerfile`,
        artifact_sha256: '2'.repeat(64),
        symbol_or_line: 'line 1',
      },
    },
    {
      evidence_id: evidenceIds.security,
      fingerprint: 'd'.repeat(64),
      source_family: 'github',
      source_locator: FIXTURE_REPOSITORY,
      immutable_revision: 'a1b2c3d4e5f67890',
      target_capability: 'security',
      support_score: 71.2,
      is_positive_support: true,
      confidence: 0.78,
      cluster_id: 'security-tests',
      confidence_factors: {
        ownership_score: 0.72,
        recency_factor: 0.91,
        source_reliability: 0.88,
        artifact_integrity: 1,
      },
      provenance: {
        artifact_path: 'tests/test_security.py',
        raw_support_text: 'Tests reject requests with missing or invalid authorization.',
        extractor_version: 'static-analyzer/2.1',
        verification_status: 'supporting observation',
        observed_at: '2026-09-21T11:00:00Z',
        artifact_url: `${FIXTURE_REPOSITORY}/blob/a1b2c3d4e5f67890/tests/test_security.py`,
        artifact_sha256: '3'.repeat(64),
        symbol_or_line: 'test_missing_authorization · lines 24–39',
      },
    },
  ];
}

function sourceReceipts(): LiveResult['sources'] {
  return [
    {
      url: FIXTURE_REPOSITORY,
      final_url: FIXTURE_REPOSITORY,
      status: 'observed',
      kind: 'github_repository',
      detail: 'Repository archive inspected at the returned commit.',
      commit_sha: 'a1b2c3d4e5f67890',
      fetched_at: '2026-09-23T04:31:00Z',
      files_inspected: 5,
      files_omitted: 2,
      evidence_count: 3,
      ownership_score: 0.72,
      acquisition_method: 'commit_archive',
      content_sha256: '4'.repeat(64),
      repository_review: {
        description: 'A bounded sample API repository.',
        stars: 18,
        forks: 4,
        open_issues: 2,
        is_fork: false,
        archived: false,
        license: 'MIT',
        topics: ['api', 'python'],
        pushed_at: '2026-09-22T09:15:00Z',
        languages_by_inspected_file: { Python: 3, Dockerfile: 1 },
        file_categories: { code: 2, tests: 1, configuration: 2 },
        dependencies: [{ name: 'fastapi', version: '0.115', path: 'requirements.txt' }],
        technologies: [{
          name: 'FastAPI',
          path: 'requirements.txt',
          basis: 'Dependency declaration returned by repository inspection.',
          url: `${FIXTURE_REPOSITORY}/blob/a1b2c3d4e5f67890/requirements.txt`,
          attribution_observed: true,
        }],
        readme_excerpt: 'A small API service with typed routes and tests.',
        engineering_signals: [{ name: 'Tests', status: 'observed', paths: ['tests/test_security.py'] }],
        limitations: ['Only five files were inspected in this bounded run.'],
      },
    },
    {
      url: FIXTURE_SECOND_REPOSITORY,
      status: 'not_scanned',
      kind: 'github_repository',
      detail: 'Repository was not inspected within the detailed-repository run limit.',
      files_inspected: 0,
      files_omitted: 1,
    },
    {
      url: 'https://www.linkedin.com/in/fixture-candidate',
      status: 'access_restricted',
      kind: 'linkedin',
      detail: 'The public page did not allow acquisition during this run.',
      verification: 'access_restricted',
    },
    {
      url: 'https://example.com/credentials/cloud-foundations',
      status: 'observed',
      kind: 'credential_page',
      detail: 'Public page text was acquired; the page does not authenticate an issuer or recipient.',
      title: 'Cloud Foundations Certificate',
      description: 'A page returned a certificate title and candidate name text.',
      excerpt: 'Certificate of completion: Cloud Foundations.',
      verification: 'possible_public_match',
      fetched_at: '2026-09-23T04:32:00Z',
      content_sha256: '5'.repeat(64),
    },
    {
      url: 'https://fixture-candidate.example.com',
      status: 'observed',
      kind: 'portfolio',
      detail: 'Public portfolio text was acquired within this bounded run.',
      title: 'Fixture Candidate · Projects',
      excerpt: 'Project index text includes the word Kubernetes; it does not establish hands-on experience.',
      verification: 'public_text_only',
      fetched_at: '2026-09-23T04:32:30Z',
      content_sha256: '6'.repeat(64),
    },
  ];
}

export function createLiveResult(intake: ResumeIntake): LiveResult {
  const observedValues: Partial<Record<CapabilityKey, number>> = {
    backend_engineering: 84.1,
    security: 59.3,
  };
  const records = evidenceRecords();
  const capabilityEstimates = Object.fromEntries(CAPABILITIES.map(capability => {
    const estimate = observedValues[capability] ?? null;
    const count = records.filter(record => record.target_capability === capability).length;
    return [capability, {
      capability_key: capability,
      estimate,
      is_observed: estimate !== null,
      effective_evidence_count: count > 0 ? Math.min(count, 1.7) : 0,
      raw_evidence_count: count,
      cluster_count: count > 0 ? 1 : 0,
      standard_error: count > 0 ? 0.11 : 0,
      dispersion: count > 1 ? 0.24 : 0,
      ci_lower: estimate === null ? null : Math.max(0, estimate - 9.2),
      ci_upper: estimate === null ? null : Math.min(100, estimate + 9.2),
      coverage_k: count > 0 ? 0.68 : 0,
    }];
  })) as unknown as LiveResult['dossier']['capability_estimates'];

  const capabilityConflicts = Object.fromEntries(CAPABILITIES.map(capability => [capability, {
    capability_key: capability,
    positive_support_sum: capability === 'security' ? 2.7 : 0,
    negative_support_sum: capability === 'security' ? 1.9 : 0,
    contradiction_diagnostic: capability === 'security' ? 0.31 : 0,
    has_meaningful_conflict: capability === 'security',
    triggering_evidence_ids: capability === 'security' ? [evidenceIds.container, evidenceIds.security] : [],
  }])) as LiveResult['dossier']['capability_conflicts'];

  const graphNodes: LiveResult['graph']['nodes'] = [
    { id: 'candidate', type: 'candidate', label: 'Fixture Candidate', properties: { candidate_id: intake.candidate_id } },
    { id: 'identity', type: 'identity', label: 'Candidate-declared GitHub identity', properties: { username: 'fixture-candidate' } },
    { id: 'run', type: 'analysis_run', label: 'Fixture analysis run', properties: { analysis_run_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc' } },
    { id: 'source-api', type: 'source', label: 'API service repository', properties: { source_locator: FIXTURE_REPOSITORY } },
    { id: 'artifact-api', type: 'artifact', label: 'app/main.py', properties: { artifact_path: 'app/main.py', immutable_revision: 'a1b2c3d4e5f67890' } },
    { id: evidenceIds.api, type: 'evidence', label: 'FastAPI route architecture', properties: { evidence_id: evidenceIds.api, source_locator: FIXTURE_REPOSITORY, artifact_path: 'app/main.py', is_positive_support: true } },
    { id: evidenceIds.container, type: 'evidence', label: 'Unpinned base image tag', properties: { evidence_id: evidenceIds.container, source_locator: FIXTURE_REPOSITORY, artifact_path: 'Dockerfile', is_positive_support: false } },
    { id: evidenceIds.security, type: 'evidence', label: 'Authorization tests', properties: { evidence_id: evidenceIds.security, source_locator: FIXTURE_REPOSITORY, artifact_path: 'tests/test_security.py', is_positive_support: true } },
    { id: 'capability-backend', type: 'capability', label: 'Backend engineering', properties: { capability_key: 'backend_engineering', is_observed: true } },
    { id: 'capability-security', type: 'capability', label: 'Security', properties: { capability_key: 'security', is_observed: true } },
    { id: 'role-requirement', type: 'role_requirement', label: 'Build reliable APIs', properties: { capability_key: 'backend_engineering', priority: 'mandatory' } },
    { id: 'interview-item', type: 'dossier_item', label: 'Security verification probe', properties: { capability_key: 'security' } },
  ];
  const graphEdges: LiveResult['graph']['edges'] = [
    { id: 'edge-1', source: 'candidate', target: 'identity', type: 'declared_identity', weight: 1, properties: {} },
    { id: 'edge-2', source: 'identity', target: 'source-api', type: 'associated_source', weight: 0.72, properties: {} },
    { id: 'edge-3', source: 'source-api', target: 'artifact-api', type: 'contains_artifact', weight: 1, properties: {} },
    { id: 'edge-4', source: 'artifact-api', target: evidenceIds.api, type: 'produced_observation', weight: 0.86, properties: {} },
    { id: 'edge-5', source: 'source-api', target: evidenceIds.container, type: 'produced_observation', weight: 0.56, properties: {} },
    { id: 'edge-6', source: evidenceIds.api, target: 'capability-backend', type: 'supports', weight: 0.84, properties: {} },
    { id: 'edge-7', source: evidenceIds.container, target: 'capability-security', type: 'contradicts', weight: 0.35, properties: {} },
    { id: 'edge-8', source: evidenceIds.security, target: 'capability-security', type: 'supports', weight: 0.71, properties: {} },
    { id: 'edge-9', source: 'role-requirement', target: 'capability-backend', type: 'weights', weight: 0.28, properties: {} },
    { id: 'edge-10', source: 'capability-security', target: 'interview-item', type: 'prompts', weight: 1, properties: {} },
  ];

  return {
    intake,
    dossier: {
      dossier_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      candidate_id: intake.candidate_id,
      analysis_run_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
      role: 'backend',
      rci: 74.6,
      coverage: 0.67,
      is_insufficient_evidence: true,
      capability_estimates: capabilityEstimates,
      capability_conflicts: capabilityConflicts,
      role_requirements: [
        { requirement_id: 'requirement-api', source_text: 'Build reliable APIs.', normalized_name: 'API design', priority: 'mandatory', capability_mappings: ['backend_engineering'], technology_mentions: ['FastAPI'] },
        { requirement_id: 'requirement-data', source_text: 'Design reliable data storage.', normalized_name: 'Database design', priority: 'preferred', capability_mappings: ['database_engineering'], technology_mentions: ['PostgreSQL'] },
      ],
      ownership_assessments: [{
        assessment_id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
        repository_url: FIXTURE_REPOSITORY,
        candidate_identifier: 'fixture-candidate',
        ownership_score: 0.72,
        feature_vector: { commit_ratio: 0.65, review_participation: 0.41 },
        is_fork: false,
        is_vendor_or_generated: false,
        attribution_confidence: 0.68,
        limitations: ['Repository-level heuristic; it does not prove authorship of individual lines.'],
      }],
      claims_corroboration: [{
        claim_id: 'claim-fastapi',
        claim_text: 'Built services with FastAPI.',
        target_capability: 'backend_engineering',
        status: 'partial',
        confidence: 0.74,
        grounding_evidence_ids: [evidenceIds.api],
        citation_urls: [FIXTURE_REPOSITORY],
        explanation: 'The repository contains related static observations; the resume statement remains self-reported.',
      }],
      interview_probes: [
        { capability_key: 'security', rank: 1, priority_score: 0.81, role_weight: 0.12, coverage_gap_term: 0.22, uncertainty_term: 0.29, contradiction_term: 0.30 },
        { capability_key: 'database_engineering', rank: 2, priority_score: 0.63, role_weight: 0.18, coverage_gap_term: 0.35, uncertainty_term: 0.28, contradiction_term: 0 },
      ],
      interview_questions: [
        { question_id: 'question-security', target_capability: 'security', question_text: 'How would you pin and update a production container base image?', rationale: 'A returned configuration observation and security test point in different directions.', verification_guidance: 'Ask about digest pinning, update cadence, and the tradeoffs involved.', grounding_evidence_ids: [evidenceIds.container, evidenceIds.security], suggested_followups: ['How would you detect a vulnerable upstream release?'] },
        { question_id: 'question-database', target_capability: 'database_engineering', question_text: 'How do you plan and roll back a schema migration?', rationale: 'The supplied sources returned limited database evidence.', verification_guidance: 'Ask for an example involving transaction boundaries and rollback.', grounding_evidence_ids: [], suggested_followups: [] },
      ],
      system_limitations: [
        'Only supplied public sources and bounded static artifacts were inspected.',
        'Repository ownership is a heuristic and does not establish identity or authorship.',
        'Candidate code is not executed.',
      ],
      versions: { platform_version: '0.1.0', scoring_config_version: '1.0.0', static_analyzer: '2.1' },
      generated_at: '2026-09-23T04:33:00Z',
      evidence_mode: 'live',
      role_weights: CAPABILITY_WEIGHTS,
      evidence_records: records,
    },
    sources: sourceReceipts(),
    graph: {
      candidate_id: intake.candidate_id,
      analysis_run_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
      nodes: graphNodes,
      edges: graphEdges,
      metadata: { returned_by_run: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc' },
    },
    graph_snapshot: null,
    status: 'partial',
    analysis: {
      method: 'bounded_static_analysis',
      coverage: { supplied_sources: 5, observed_sources: 2, skills_declared: 3, skills_with_repository_matches: 1, credential_claims: 1 },
      skills: [
        { skill: 'Python', learning: false, status: 'repository_support', evidence: [{ name: 'FastAPI', path: 'requirements.txt', basis: 'Dependency declaration', url: `${FIXTURE_REPOSITORY}/blob/a1b2c3d4e5f67890/requirements.txt`, attribution_observed: true }], evidence_count: 1, public_mentions: [], explanation: 'A related repository signal was returned.' },
        { skill: 'Docker', learning: true, status: 'repository_only', evidence: [], evidence_count: 0, public_mentions: [], explanation: 'The resume declaration is not corroborated by a returned artifact.' },
        { skill: 'Kubernetes', learning: false, status: 'public_mention_only', evidence: [], evidence_count: 0, public_mentions: ['Public portfolio text'], explanation: 'A public text mention is not independent verification.' },
      ],
      credentials: [{
        claim: 'Cloud Foundations Certificate',
        status: 'possible_public_match',
        explanation: 'A public text match does not authenticate issuer, recipient, dates, or validity.',
        matching_pages: [{ url: 'https://example.com/credentials/cloud-foundations', title: 'Cloud Foundations Certificate', matched_terms: ['Cloud Foundations'], candidate_name_present: true }],
      }],
      projects: [{ title: 'API Service', description: 'A resume-declared API project.', source_urls: [FIXTURE_REPOSITORY], status: 'linked_sources', explanation: 'A linked source was returned; the project claim is not thereby authenticated.' }],
      education: [{ claim: 'BSc Computer Science', status: 'self_reported' }],
      experience: [{ claim: 'Software Engineer', status: 'self_reported' }],
      achievements: [],
      quantified_claims_to_verify: ['Built 10+ projects'],
      next_steps: ['Discuss the container update strategy.', 'Ask for a database migration example.'],
    },
  };
}
