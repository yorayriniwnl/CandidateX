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
    display_name: 'Example Candidate One',
    primary_email: 'candidate-one@example.invalid',
    role: MOCK_DOSSIER.role,
    has_completed_dossier: true,
    coverage: MOCK_DOSSIER.coverage,
    has_meaningful_conflict: Object.values(MOCK_DOSSIER.capability_conflicts).some((item) => item.has_meaningful_conflict),
    created_at: MOCK_DOSSIER.generated_at,
    source: 'sample',
  },
  {
    id: 'hr-sample-two', display_name: 'Example Candidate Two', primary_email: 'candidate-two@example.invalid', role: 'frontend',
    has_completed_dossier: false, has_meaningful_conflict: false,
    created_at: '', source: 'sample',
  },
  {
    id: 'hr-sample-three', display_name: 'Example Candidate Three', primary_email: 'candidate-three@example.invalid', role: 'ml_engineer',
    has_completed_dossier: false, has_meaningful_conflict: false,
    created_at: '', source: 'sample',
  },
  {
    id: 'hr-sample-four', display_name: 'Example Candidate Four', primary_email: 'candidate-four@example.invalid', role: 'devops_cloud',
    has_completed_dossier: false, has_meaningful_conflict: false,
    created_at: '', source: 'sample',
  },
  {
    id: 'hr-sample-five', display_name: 'Example Candidate Five', primary_email: 'candidate-five@example.invalid', role: 'fullstack',
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

export function summarizeDossier(dossier: Dossier) {
  const claims = dossier.claims_corroboration;
  const strengths = [...new Set(claims.filter((claim) => claim.status === 'corroborated')
    .map((claim) => `${CAPABILITY_LABELS[claim.target_capability]}: supported by the supplied evidence.`))];
  const discussion = [...new Set(claims.filter((claim) => claim.status === 'partial')
    .map((claim) => `${CAPABILITY_LABELS[claim.target_capability]}: ask which parts the candidate personally delivered.`))];
  const alerts = [...new Set([
    ...Object.values(dossier.capability_conflicts).filter((item) => item.has_meaningful_conflict)
      .map((item) => `${CAPABILITY_LABELS[item.capability_key]}: the available evidence gives mixed signals. Review with the candidate.`),
    ...claims.filter((claim) => claim.status === 'contradicted' || claim.status === 'unknown')
      .map((claim) => `${CAPABILITY_LABELS[claim.target_capability]}: ${claim.status === 'unknown' ? 'a stated skill is not yet supported by evidence.' : 'a stated skill does not fully match the supplied evidence.'}`),
    ...(dossier.is_insufficient_evidence ? ['More work samples are needed before drawing conclusions.'] : []),
  ])];
  return { strengths, discussion, alerts };
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
