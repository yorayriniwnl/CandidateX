import type { CandidateSummary } from '../../lib/api';
import { TEAM_CANDIDATES, normalizeTeamMember } from '../../lib/team-members';
import type { CandidateManifest, CanonicalRole, CapabilityKey, Dossier, CEGGraph } from '../../types/cci';

export const ROLE_LABELS: Record<CanonicalRole, string> = {
  backend: 'Backend Developer',
  frontend: 'Frontend Developer',
  fullstack: 'Full-Stack Developer',
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
  dossier?: Dossier;
  graph?: CEGGraph;
}

export const HR_STORAGE_KEY = 'cci_hr_saved_candidates';
export const LEGACY_STORAGE_KEY = 'cci_hr_candidates';

export function toTitleCase(text: string): string {
  return text
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

export function sanitizeCandidateForStorage(candidate: HRCandidate): HRCandidate {
  const { graph: _unusedGraph, dossier, manifest, ...rest } = candidate;

  let sanitizedDossier: Dossier | undefined = undefined;
  if (dossier) {
    // Keep only compact summary fields needed for display/export; strip heavy arrays
    sanitizedDossier = {
      dossier_id: dossier.dossier_id || `dossier-${dossier.candidate_id}`,
      analysis_run_id: dossier.analysis_run_id,
      candidate_id: dossier.candidate_id,
      role: (dossier.role || candidate.role) as CanonicalRole,
      generated_at: dossier.generated_at,
      evidence_mode: dossier.evidence_mode,
      rci: dossier.rci,
      coverage: dossier.coverage,
      is_insufficient_evidence: dossier.is_insufficient_evidence,
      capability_estimates: dossier.capability_estimates,
      capability_conflicts: dossier.capability_conflicts,
      role_requirements: Array.isArray(dossier.role_requirements) ? dossier.role_requirements.slice(0, 10) : [],
      role_fit: dossier.role_fit,
      analysis_confidence: dossier.analysis_confidence,
      ownership_assessments: Array.isArray(dossier.ownership_assessments)
        ? dossier.ownership_assessments.slice(0, 5)
        : [],
      claims_corroboration: Array.isArray(dossier.claims_corroboration)
        ? dossier.claims_corroboration.slice(0, 20)
        : [],
      interview_probes: Array.isArray(dossier.interview_probes)
        ? dossier.interview_probes.slice(0, 10)
        : [],
      interview_questions: Array.isArray(dossier.interview_questions)
        ? dossier.interview_questions.slice(0, 10)
        : [],
      system_limitations: Array.isArray(dossier.system_limitations) ? dossier.system_limitations : [],
      versions: dossier.versions || {},
    };
  }

  let sanitizedManifest: CandidateManifest | undefined = undefined;
  if (manifest) {
    sanitizedManifest = {
      candidate_id: manifest.candidate_id,
      full_name: manifest.full_name,
      primary_email: manifest.primary_email,
      picture: manifest.picture,
      github_usernames: manifest.github_usernames,
      github_repositories: manifest.github_repositories,
      deployment_urls: manifest.deployment_urls,
      portfolio_urls: manifest.portfolio_urls,
      declared_skills: manifest.declared_skills,
      extraction_metadata: manifest.extraction_metadata,
    };
  }

  return {
    ...rest,
    manifest: sanitizedManifest,
    dossier: sanitizedDossier,
    // Graph is always fetched dynamically from backend API; never persisted in localStorage
    graph: undefined,
  };
}

function persistCandidatesToStorage(candidates: HRCandidate[]): void {
  if (typeof window === 'undefined') return;

  // Always remove legacy duplicate key to immediately release quota pressure
  try {
    localStorage.removeItem(LEGACY_STORAGE_KEY);
  } catch {}

  const sanitized = candidates.map(sanitizeCandidateForStorage);

  // Tier 1: Try persisting clean sanitized candidates
  try {
    localStorage.setItem(HR_STORAGE_KEY, JSON.stringify(sanitized));
    return;
  } catch (err: any) {
    if (err?.name !== 'QuotaExceededError' && err?.code !== 22 && err?.code !== 1014) {
      console.warn('Could not write candidates to localStorage', err);
      return;
    }
  }

  // Tier 2: Strip dossiers completely, storing only essential summary fields
  try {
    const compactSummaryOnly = sanitized.map(({ dossier: _d, ...base }) => base);
    localStorage.setItem(HR_STORAGE_KEY, JSON.stringify(compactSummaryOnly));
    return;
  } catch (err: any) {
    if (err?.name !== 'QuotaExceededError' && err?.code !== 22 && err?.code !== 1014) {
      console.warn('Could not write candidate summaries to localStorage', err);
      return;
    }
  }

  // Tier 3: Limit saved candidates to the 10 most recent entries
  try {
    const trimmed = sanitized.slice(0, 10).map(({ dossier: _d, ...base }) => base);
    localStorage.setItem(HR_STORAGE_KEY, JSON.stringify(trimmed));
  } catch (err) {
    console.warn('localStorage quota exhausted; candidate saved to backend DB but skipped local cache', err);
  }
}

export function getSavedHRCandidates(): HRCandidate[] {
  if (typeof window === 'undefined') return [];
  try {
    const rawLegacy = localStorage.getItem(LEGACY_STORAGE_KEY);
    const rawPrimary = localStorage.getItem(HR_STORAGE_KEY);

    const raw = rawPrimary || rawLegacy;
    if (!raw) return [];

    let parsed: any[];
    try {
      parsed = JSON.parse(raw);
    } catch {
      return [];
    }

    if (!Array.isArray(parsed)) return [];

    let needsCleanup = !!rawLegacy;
    const sanitized = parsed.map((item) => {
      if (item?.graph || (item?.dossier?.evidence_records && item.dossier.evidence_records.length > 0)) {
        needsCleanup = true;
      }
      return sanitizeCandidateForStorage(item);
    });

    // Actively recover quota if legacy key or bloated items were present
    if (needsCleanup) {
      try {
        localStorage.removeItem(LEGACY_STORAGE_KEY);
        localStorage.setItem(HR_STORAGE_KEY, JSON.stringify(sanitized));
      } catch {
        // Safe to ignore on passive read
      }
    }

    return sanitized;
  } catch (e) {
    console.warn('Failed to load saved candidates from localStorage', e);
    return [];
  }
}

export function saveHRCandidate(candidate: HRCandidate): void {
  if (typeof window === 'undefined') return;
  try {
    const existing = getSavedHRCandidates();
    const candEmail = candidate.primary_email?.trim().toLowerCase();
    const candName = candidate.display_name?.trim().toLowerCase();

    // Deduplicate by ID, Email, or normalized Name to prevent repeated candidate profiles
    const filtered = existing.filter((c) => {
      if (c.id === candidate.id) return false;
      const cEmail = c.primary_email?.trim().toLowerCase();
      if (candEmail && cEmail && cEmail === candEmail) return false;
      const cName = c.display_name?.trim().toLowerCase();
      if (candName && cName && cName === candName) return false;
      return true;
    });

    const updated = [candidate, ...filtered];
    persistCandidatesToStorage(updated);
    window.dispatchEvent(new CustomEvent('cci_hr_candidates_changed', { detail: candidate }));
  } catch (e) {
    console.warn('Failed to save HR candidate to localStorage', e);
  }
}

export function removeSavedHRCandidate(candidateId: string): void {
  if (typeof window === 'undefined') return;
  try {
    const existing = getSavedHRCandidates();
    const updated = existing.filter((c) => c.id !== candidateId);
    persistCandidatesToStorage(updated);
    window.dispatchEvent(new CustomEvent('cci_hr_candidates_changed', { detail: { id: candidateId, removed: true } }));
  } catch (e) {
    console.warn('Failed to remove HR candidate from localStorage', e);
  }
}

export function saveReviewToHR(params: {
  candidateId: string;
  displayName: string;
  email?: string | null;
  role: string;
  rci?: number | null;
  jdFitScore?: number | null;
  observedCapabilities?: number;
  coverage?: number | null;
  hasMeaningfulConflict?: boolean;
  manifest?: CandidateManifest;
  dossier?: Dossier;
  graph?: CEGGraph;
  [key: string]: unknown;
}): HRCandidate {
  const observedCount = params.observedCapabilities ?? (params.dossier?.capability_estimates
    ? Object.values(params.dossier.capability_estimates).filter((e) => e.is_observed && e.estimate != null).length
    : params.coverage != null
    ? Math.max(1, Math.round(params.coverage * 12))
    : undefined);

  const fitScore = params.jdFitScore ?? params.rci ?? params.dossier?.rci;

  const normalizedMember = normalizeTeamMember({
    id: params.candidateId,
    display_name: params.displayName ? toTitleCase(params.displayName) : 'Candidate',
    primary_email: params.email?.trim() || undefined,
    role: params.role,
    role_label: ROLE_LABELS[params.role as CanonicalRole] || params.role,
    has_completed_dossier: true,
    has_meaningful_conflict: false,
    created_at: '',
  });

  const hrCandidate: HRCandidate = {
    id: params.candidateId,
    display_name: normalizedMember.display_name,
    primary_email: normalizedMember.primary_email,
    role: params.role,
    role_label: normalizedMember.role_label || ROLE_LABELS[params.role as CanonicalRole] || params.role,
    has_completed_dossier: true,
    rci: params.rci ?? params.dossier?.rci ?? undefined,
    jd_fit_score: fitScore ?? undefined,
    observed_capabilities: observedCount,
    coverage: params.coverage ?? params.dossier?.coverage ?? undefined,
    has_meaningful_conflict: params.hasMeaningfulConflict ?? (params.dossier?.capability_conflicts
      ? Object.values(params.dossier.capability_conflicts).some((c) => c.has_meaningful_conflict)
      : false),
    created_at: params.dossier?.generated_at || new Date().toISOString(),
    source: 'live',
    manifest: params.manifest,
    dossier: params.dossier,
    graph: params.graph,
  };

  saveHRCandidate(hrCandidate);
  return hrCandidate;
}

// Keep all six configured members available when their saved records are absent.
export const SAMPLE_CANDIDATES: HRCandidate[] = TEAM_CANDIDATES.map((candidate) => ({
  ...candidate,
  source: 'sample' as const,
}));

export function roleLabel(role?: string) {
  if (!role || role === 'Role not specified') return '—';
  return ROLE_LABELS[role as CanonicalRole] || role;
}

export function evaluationLabel(candidate: HRCandidate) {
  if (candidate.source === 'draft') return 'Local draft';
  return candidate.has_completed_dossier ? 'Completed' : 'Pending';
}

export function evidenceLabel(candidate: HRCandidate) {
  if (!candidate.has_completed_dossier) return 'Pending audit';
  if (candidate.has_meaningful_conflict) return 'Needs review';
  if (candidate.coverage == null) return 'Not reported';
  return candidate.coverage > 0 ? 'Available to review' : 'No evidence found';
}

export function hasEvidenceAlert(candidate: HRCandidate) {
  return candidate.has_completed_dossier && (candidate.has_meaningful_conflict || candidate.coverage === 0);
}

export function summarizeDossier(dossier: Dossier) {
  const claims = dossier.claims_corroboration || [];
  const strengths = [...new Set(claims.filter((claim) => claim.status === 'corroborated')
    .map((claim) => `${CAPABILITY_LABELS[claim.target_capability] || claim.target_capability}: supported by the supplied evidence.`))];
  const discussion = [...new Set(claims.filter((claim) => claim.status === 'partial')
    .map((claim) => `${CAPABILITY_LABELS[claim.target_capability] || claim.target_capability}: ask which parts the candidate personally delivered.`))];
  const alerts = [...new Set([
    ...Object.values(dossier.capability_conflicts || {}).filter((item) => item.has_meaningful_conflict)
      .map((item) => `${CAPABILITY_LABELS[item.capability_key] || item.capability_key}: the available evidence gives mixed signals. Review with the candidate.`),
    ...claims.filter((claim) => claim.status === 'contradicted' || claim.status === 'unknown')
      .map((claim) => `${CAPABILITY_LABELS[claim.target_capability] || claim.target_capability}: ${claim.status === 'unknown' ? 'a stated skill is not yet supported by evidence.' : 'a stated skill does not fully match the supplied evidence.'}`),
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
