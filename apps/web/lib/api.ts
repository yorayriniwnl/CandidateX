/**
 * Candidate Capability Intelligence (CCI) - Frontend API Client
 * Connects the Next.js UI to the FastAPI backend with graceful fallback.
 */

import {
  CanonicalRole,
  CapabilityKey,
  Dossier,
  CEGGraph,
  CandidateManifest,
  NormalizedRequirement,
  ProbeEvaluationItem,
  HiringRecommendation,
  InterviewFeedbackPayload,
  InterviewFeedbackResponse,
  AuditEventItem,
  TheoremMetadata,
  AblationStudyResponse,
  CalculationRequest,
  CalculationResponse,
} from '../types/cci';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export interface CandidateSummary {
  id: string;
  display_name: string;
  primary_email?: string;
  has_completed_dossier: boolean;
  rci?: number | null;
  jd_fit_score?: number | null;
  observed_capabilities?: number;
  coverage?: number;
  role?: string;
  role_label?: string;
  has_meaningful_conflict: boolean;
  created_at: string;
}

export interface JobParseResponse {
  role: CanonicalRole;
  requirements_count: number;
  requirements: NormalizedRequirement[];
  role_profile: {
    canonical_role: CanonicalRole;
    raw_importances: Record<CapabilityKey, number>;
    softmax_weights: Record<CapabilityKey, number>;
  };
}

export interface PipelineStatusResponse {
  analysis_run_id: string;
  candidate_id: string;
  role: CanonicalRole;
  status: 'pending' | 'running' | 'completed' | 'failed';
  current_stage?: string;
  stages: {
    stage: string;
    label: string;
    status: string;
    started_at?: string;
    completed_at?: string;
    details?: string;
  }[];
  dossier_id?: string;
  rci?: number;
  coverage?: number;
  error?: string;
}

/**
 * Checks if the backend API server is online and responding.
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Initiates the 10-stage analysis pipeline on the backend.
 */
export async function triggerPipelineRun(
  candidateId: string,
  role: CanonicalRole,
  manifest?: CandidateManifest,
  jdText?: string,
  cvText?: string
): Promise<PipelineStatusResponse> {
  const payload = {
    candidate_id: candidateId,
    role: role,
    jd_text: jdText || '',
    cv_text: cvText || '',
    repo_urls: [
      ...(manifest?.github_repositories || []),
    ],
    declared_claims: manifest?.declared_skills || [],
  };

  const res = await fetch(`${API_BASE_URL}/api/v1/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Pipeline initiation failed: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Retrieves the current status and stage progress of an analysis run.
 */
export async function fetchPipelineStatus(runId: string): Promise<PipelineStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/pipeline/status/${runId}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch status for run ${runId}: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Fetches the synthesized Technical Dossier for a candidate.
 */
export async function fetchCandidateDossier(candidateId: string): Promise<Dossier> {
  const res = await fetch(`${API_BASE_URL}/api/v1/dossier/${candidateId}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });

  if (!res.ok) {
    throw new Error(`Dossier fetch failed: HTTP ${res.status}`);
  }

  const data = await res.json();
  return data.dossier || data;
}

/**
 * Fetches the Candidate Evidence Graph (CEG) projection.
 */
export async function fetchCandidateGraph(candidateId: string): Promise<CEGGraph> {
  const res = await fetch(`${API_BASE_URL}/api/v1/dossier/${candidateId}/graph`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });

  if (!res.ok) {
    throw new Error(`Graph fetch failed: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Triggers a pure functional rescore of a candidate's dossier with updated weights.
 */
export async function rescoreDossierBackend(
  runId: string,
  newWeights: Record<CapabilityKey, number>
): Promise<Dossier> {
  const res = await fetch(`${API_BASE_URL}/api/v1/pipeline/rescore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      run_id: runId,
      weights: newWeights,
    }),
  });

  if (!res.ok) {
    throw new Error(`Functional rescore failed: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Parses raw Job Description text into structured requirements and role weights.
 */
export async function parseJobDescription(
  jdText: string,
  role: CanonicalRole = 'backend'
): Promise<JobParseResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jd_text: jdText, role }),
  });

  if (!res.ok) {
    throw new Error(`Job parse failed: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Lists candidates from the database with evaluation and dossier summary.
 */
export async function fetchCandidatesList(): Promise<CandidateSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/candidates`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });

  if (!res.ok) {
    throw new Error(`Candidates list fetch failed: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Deletes a candidate by ID from the backend.
 */
export async function deleteCandidate(candidateId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/candidates/${candidateId}`, {
    method: 'DELETE',
  });
  if (!res.ok && res.status !== 404) {
    throw new Error(`Failed to delete candidate: HTTP ${res.status}`);
  }
}

/**
 * Purges non-team candidates from the backend, preserving only the 6 team members.
 */
export async function purgeNonTeamCandidates(): Promise<{ deleted: number }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/candidates?keep_team_only=true`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`Failed to purge candidates: HTTP ${res.status}`);
  }
  return res.json();
}

export type ExportFormat = 'html' | 'markdown' | 'json' | 'csv';
export type ExportScope = 'report' | 'audit' | 'full';

/**
 * Constructs the export endpoint URL for the given candidate, format, and scope.
 */
export function getExportDossierUrl(
  candidateId: string,
  format: ExportFormat = 'html',
  scope: ExportScope = 'report'
): string {
  return `${API_BASE_URL}/api/v1/dossier/${candidateId}/export?format=${format}&scope=${scope}`;
}

/**
 * Constructs the dedicated audit export endpoint URL for the candidate.
 */
export function getExportAuditUrl(
  candidateId: string,
  format: ExportFormat = 'json'
): string {
  return `${API_BASE_URL}/api/v1/overrides/audit/${candidateId}/export?format=${format}`;
}

/**
 * Downloads the exported dossier report, full audit, or combined bundle.
 */
export async function downloadDossier(
  candidateId: string,
  format: ExportFormat = 'html',
  candidateName: string = 'candidate',
  scope: ExportScope = 'report'
): Promise<void> {
  const url = getExportDossierUrl(candidateId, format, scope);
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to export ${scope}: HTTP ${res.status}`);
  }

  const blob = await res.blob();
  const extMap: Record<ExportFormat, string> = {
    html: 'html',
    markdown: 'md',
    json: 'json',
    csv: 'csv',
  };
  const ext = extMap[format] || 'txt';
  const cleanName = candidateName.toLowerCase().replace(/[^a-z0-9]/g, '_');
  const scopeSuffix =
    scope === 'audit'
      ? 'full_audit'
      : scope === 'full'
      ? 'report_and_full_audit'
      : 'technical_report';
  const filename = `${cleanName}_${scopeSuffix}.${ext}`;

  const link = document.createElement('a');
  link.href = window.URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(link.href);
}

/**
 * Downloads the candidate's full audit and governance log directly.
 */
export async function downloadFullAudit(
  candidateId: string,
  format: ExportFormat = 'html',
  candidateName: string = 'candidate'
): Promise<void> {
  return downloadDossier(candidateId, format, candidateName, 'audit');
}

/**
 * Downloads the combined Report and Full Audit package.
 */
export async function downloadReportAndAudit(
  candidateId: string,
  format: ExportFormat = 'html',
  candidateName: string = 'candidate'
): Promise<void> {
  return downloadDossier(candidateId, format, candidateName, 'full');
}

export interface RecruiterOverridePayload {
  candidate_id: string;
  role_weights: Record<string, number>;
  justification: string;
  user_id?: string;
  organization_id?: string;
}

export interface RecruiterOverrideResponse {
  graph: CEGGraph;
  persistence: 'session' | 'database';
  override_id: string;
  candidate_id: string;
  previous_rci: number | null;
  rescored_rci: number | null;
  rescored_coverage: number;
  audit_event_id: string;
  justification: string;
  recorded_at: string;
  dossier: Dossier;
}

/**
 * Submits recruiter role weight overrides to backend with mandatory audit justification.
 */
export async function submitRecruiterOverride(
  payload: RecruiterOverridePayload
): Promise<RecruiterOverrideResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/overrides/recruiter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Recruiter override failed: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Submits technical interviewer probe evaluations and hiring recommendation to immutable audit trail.
 */
export async function submitInterviewFeedback(
  payload: InterviewFeedbackPayload
): Promise<InterviewFeedbackResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/overrides/interview-feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Interview feedback submission failed: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Fetches the immutable audit trail of recruiter overrides and interview feedback for a candidate.
 */
export async function fetchCandidateAuditTrail(
  candidateId: string
): Promise<AuditEventItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/overrides/audit/${candidateId}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch candidate audit trail: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Fetches all 10 conference paper theorems with LaTeX formulas and invariant descriptions.
 */
export async function fetchTheorems(): Promise<TheoremMetadata[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/research/theorems`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    next: { revalidate: 3600 },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch theorems catalog: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Fetches Table 1 Model Architecture Ablation Study reproduction data.
 */
export async function fetchAblationStudy(): Promise<AblationStudyResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/research/ablation-study`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    next: { revalidate: 3600 },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch ablation study: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Evaluates live mathematical calculation for paper theorems on the backend.
 */
export async function calculateTheoremMath(
  req: CalculationRequest
): Promise<CalculationResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/research/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    throw new Error(`Theorem calculation failed: HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Saves or updates a candidate profile in the backend directory.
 */
export async function saveCandidateBackend(
  candidate: CandidateSummary & { manifest?: CandidateManifest }
): Promise<CandidateSummary> {
  const payload = {
    id: candidate.id,
    display_name: candidate.display_name,
    primary_email: candidate.primary_email,
    has_completed_dossier: candidate.has_completed_dossier,
    rci: candidate.rci,
    coverage: candidate.coverage,
    role: candidate.role,
    has_meaningful_conflict: candidate.has_meaningful_conflict,
    created_at: candidate.created_at,
    manifest_data: candidate.manifest,
  };

  const res = await fetch(`${API_BASE_URL}/api/v1/candidates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Failed to save candidate to backend: HTTP ${res.status}`);
  }

  return res.json();
}

export interface JobUploadResponse {
  id: string;
  title: string;
  canonical_role: string;
  is_active: boolean;
  created_at: string;
  file_name: string;
  requirements_count: number;
}

/**
 * Uploads a Job Description file (PDF or DOCX) to the backend.
 * The backend extracts text and recruitment rules, stores them in the database,
 * and returns only a minimal confirmation — no document content is exposed.
 */
export async function uploadJobDescription(
  file: File,
  title: string,
  role: CanonicalRole = 'backend'
): Promise<JobUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title);
  formData.append('role', role);

  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`Job upload failed: HTTP ${res.status}${detail ? ` — ${detail}` : ''}`);
  }

  return res.json();
}

