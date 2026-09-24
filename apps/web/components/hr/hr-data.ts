// SYNTHETIC DEMONSTRATION DATA
import type { CandidateSummary } from '../../lib/api';
import type { CandidateManifest, CanonicalRole, CapabilityKey, Dossier } from '../../types/cci';
import { MOCK_DOSSIER } from '../../data/mockDossier';

export const ROLE_LABELS: Record<CanonicalRole, string> = {
  backend: 'Backend Developer',
  frontend: 'Frontend Developer',
  fullstack: 'Full-stack Developer',
  ml_engineer: 'Machine Learning Engineer',
  devops_cloud: 'Cloud & Operations Engineer',
  data_engineer: 'Data Engineer',
};

const CAPABILITY_LABELS: Record<CapabilityKey, string> = {
  backend_engineering: 'Backend development',
  frontend_engineering: 'Frontend development',
  database_engineering: 'Database design',
  devops_cloud: 'Cloud & operations',
  machine_learning: 'Machine learning',
  data_engineering: 'Data engineering',
  algorithms_problem_solving: 'Problem solving',
  testing_quality: 'Testing & quality',
  security: 'Application security',
  software_architecture: 'Software design',
  collaboration: 'Teamwork',
  documentation_communication: 'Documentation & communication',
};

export interface HRCandidate extends CandidateSummary {
  source: 'live' | 'sample' | 'draft';
  manifest?: CandidateManifest;
}

// Only this sample is associated with the repository's exported mock dossier.
export const SAMPLE_CANDIDATES: HRCandidate[] = [
  {
    id: MOCK_DOSSIER.candidate_id,
    display_name: 'Jordan Example (SYNTHETIC DEMONSTRATION DATA)',
    primary_email: 'jordan@example.test',
    role: MOCK_DOSSIER.role,
    has_completed_dossier: true,
    coverage: MOCK_DOSSIER.coverage,
    has_meaningful_conflict: Object.values(MOCK_DOSSIER.capability_conflicts).some((item) => item.has_meaningful_conflict),
    created_at: MOCK_DOSSIER.generated_at,
    source: 'sample',
  },
  {
    id: 'hr-sample-alex', display_name: 'Alex Rivera (SYNTHETIC DEMONSTRATION DATA)', primary_email: 'alex@example.test', role: 'frontend',
    has_completed_dossier: false, has_meaningful_conflict: false,
    created_at: '', source: 'sample',
  },
  {
    id: 'hr-sample-morgan', display_name: 'Morgan Lee (SYNTHETIC DEMONSTRATION DATA)', primary_email: 'morgan@example.test', role: 'ml_engineer',
    has_completed_dossier: false, has_meaningful_conflict: false,
    created_at: '', source: 'sample',
  },
  {
    id: 'hr-sample-taylor', display_name: 'Taylor Casey (SYNTHETIC DEMONSTRATION DATA)', primary_email: 'taylor@example.test', role: 'devops_cloud',
    has_completed_dossier: false, has_meaningful_conflict: false,
    created_at: '', source: 'sample',
  },
  {
    id: 'hr-sample-sam', display_name: 'Sam Vance (SYNTHETIC DEMONSTRATION DATA)', primary_email: 'sam@example.test', role: 'fullstack',
    has_completed_dossier: false, has_meaningful_conflict: false,
    created_at: '', source: 'sample',
  },
];

export function roleLabel(role?: string) {
  return ROLE_LABELS[role as CanonicalRole] || 'Role not specified';
}

export function evaluationLabel(candidate: HRCandidate) {
  if (candidate.source === 'draft') return 'Local draft';
  return candidate.has_completed_dossier ? 'Completed' : 'Not completed';
}

export function evidenceLabel(candidate: HRCandidate) {
  if (!candidate.has_completed_dossier) return 'Awaiting evaluation';
  if (candidate.has_meaningful_conflict) return 'Needs review';
  if (candidate.coverage == null) return 'Not reported';
  return candidate.coverage > 0 ? 'Available to review' : 'No evidence found';
}

export function hasEvidenceAlert(candidate: HRCandidate) {
  return candidate.has_completed_dossier && (candidate.has_meaningful_conflict || candidate.coverage === 0);
}

export interface HRDecisionSupportSummary {
  evidenceAvailable: string[];
  unresolvedClaims: string[];
  roleStrengths: string[];
  uncertainty: string[];
  evidenceGaps: string[];
  contradictions: string[];
  interviewQuestions: string[];
  // Legacy aliases
  strengths: string[];
  discussion: string[];
  alerts: string[];
}

export function summarizeDossier(dossier: Dossier): HRDecisionSupportSummary {
  const claims = dossier.claims_corroboration || [];

  // 1. Evidence Available
  const evidenceAvailable = [
    `Evidence coverage: ${(dossier.coverage * 100).toFixed(1)}% across ${Object.keys(dossier.capability_estimates || {}).length} technical dimensions.`,
    `${dossier.evidence_records?.length || 0} immutable evidence records indexed from inspected sources.`,
    `${dossier.project_entities?.length || 0} project entities and ${dossier.ownership_assessments?.length || 0} repository ownership records attributed.`,
  ];

  // 2. Unresolved Claims (Declarations lacking independent proof)
  const unresolvedClaims = [...new Set(
    claims
      .filter((claim) => claim.status === 'unknown' || claim.status === 'partial')
      .map((claim) => {
        const cap = CAPABILITY_LABELS[claim.target_capability] || claim.target_capability;
        return claim.status === 'unknown'
          ? `${cap}: candidate-declared skill has no independent artifact corroboration.`
          : `${cap}: partially corroborated; candidate self-declaration lacks independent confirmation.`;
      })
  )];

  // 3. Role-Relevant Strengths Observed
  const roleStrengths = [...new Set(
    claims
      .filter((claim) => claim.status === 'corroborated')
      .map((claim) => `${CAPABILITY_LABELS[claim.target_capability] || claim.target_capability}: supported by observed repository/deployment evidence.`)
  )];

  // 4. Uncertainty
  const uncertainty = [
    ...(dossier.is_insufficient_evidence
      ? ['Overall evidence coverage is below sufficiency threshold. Missing evidence represents UNKNOWN capability, never low capability.']
      : []),
    ...Object.values(dossier.capability_estimates || {})
      .filter((c) => c.is_observed && c.ci_lower !== null && c.ci_upper !== null && (c.ci_upper - c.ci_lower) > 0.35)
      .map((c) => `${CAPABILITY_LABELS[c.capability_key] || c.capability_key}: wide estimation interval [${((c.ci_lower || 0) * 100).toFixed(0)}%–${((c.ci_upper || 0) * 100).toFixed(0)}%] due to bounded sample size.`),
  ];

  // 5. Evidence Gaps
  const evidenceGaps = Object.entries(dossier.capability_estimates || {})
    .filter(([_, c]) => !c.is_observed)
    .map(([key, _]) => `${CAPABILITY_LABELS[key as CapabilityKey] || key}: no public artifacts observed in bounded scope.`);

  // 6. Contradictions
  const contradictions = [...new Set([
    ...Object.values(dossier.capability_conflicts || {})
      .filter((item) => item.has_meaningful_conflict)
      .map((item) => `${CAPABILITY_LABELS[item.capability_key] || item.capability_key}: discrepancy detected between declared claim and observed artifacts.`),
    ...claims
      .filter((claim) => claim.status === 'contradicted')
      .map((claim) => `${CAPABILITY_LABELS[claim.target_capability] || claim.target_capability}: artifact observation contradicts candidate assertion.`),
  ])];

  // 7. Interview Questions
  const interviewQuestions = (dossier.interview_questions || []).map((q) => q.question_text);

  return {
    evidenceAvailable,
    unresolvedClaims,
    roleStrengths,
    uncertainty,
    evidenceGaps,
    contradictions,
    interviewQuestions,
    // Legacy aliases
    strengths: roleStrengths,
    discussion: unresolvedClaims,
    alerts: [...contradictions, ...uncertainty],
  };
}

// Bound read-only requests without changing shared API utilities. Late results are ignored.
export async function withReadTimeout<T>(request: Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      request,
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error('Request timed out')), 10000);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}
