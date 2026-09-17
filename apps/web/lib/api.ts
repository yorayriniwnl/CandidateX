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
} from '../types/cci';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface CandidateSummary {
  id: string;
  display_name: string;
  primary_email?: string;
  has_completed_dossier: boolean;
  rci?: number;
  coverage?: number;
  role?: string;
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
  jdText?: string
): Promise<PipelineStatusResponse> {
  const payload = {
    candidate_id: candidateId,
    role: role,
    jd_text: jdText || '',
    cv_text: manifest?.declared_skills ? `Candidate Skills: ${manifest.declared_skills.join(', ')}` : '',
    repo_urls: [
      ...(manifest?.github_repositories || []),
      ...(manifest?.deployment_urls || []),
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
 * Constructs the export endpoint URL for the given candidate and format.
 */
export function getExportDossierUrl(
  candidateId: string,
  format: 'html' | 'markdown' | 'json' = 'html'
): string {
  return `${API_BASE_URL}/api/v1/dossier/${candidateId}/export?format=${format}`;
}

/**
 * Downloads the exported dossier file directly to the client browser.
 */
export async function downloadDossier(
  candidateId: string,
  format: 'html' | 'markdown' | 'json',
  candidateName: string = 'candidate'
): Promise<void> {
  const url = getExportDossierUrl(candidateId, format);
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to export dossier: HTTP ${res.status}`);
  }

  const blob = await res.blob();
  const ext = format === 'html' ? 'html' : format === 'markdown' ? 'md' : 'json';
  const cleanName = candidateName.toLowerCase().replace(/[^a-z0-9]/g, '_');
  const filename = `${cleanName}_technical_brief.${ext}`;

  const link = document.createElement('a');
  link.href = window.URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(link.href);
}

export interface RecruiterOverridePayload {
  candidate_id: string;
  role_weights: Record<string, number>;
  justification: string;
  user_id?: string;
  organization_id?: string;
}

export interface RecruiterOverrideResponse {
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
