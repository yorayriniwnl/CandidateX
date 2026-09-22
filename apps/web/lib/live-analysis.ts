import type { AnalysisConfidenceSummary, CEGGraph, Dossier, RoleFitSummary } from '../types/cci';
import type { Evidence } from './evidence';

export interface ResumeIntake {
  candidate_id: string;
  manifest: {
    display_name: string; email: string | null; claimed_skills: string[];
    github_urls: string[]; linkedin_urls: string[]; coding_profile_urls: string[];
    credential_urls: string[]; deployment_urls: string[]; portfolio_urls: string[]; project_links: string[];
    project_claims: { title: string; description: string; technologies: string[] }[];
  };
  filename: string; document_sha256: string; text_preview: string; warnings: string[]; storage: string;
  resume_review: { sections: Record<string, string[]>; learning_skills: string[]; observations: string[] };
}
export interface TechnologyEvidence { name: string; path: string; basis: string; url: string; attribution_observed?: boolean; }
export interface RepositoryReview {
  description: string | null; stars: number; forks: number; open_issues: number; is_fork: boolean; archived: boolean;
  license: string | null; topics: string[]; pushed_at: string | null; languages_by_inspected_file: Record<string, number>;
  file_categories: Record<string, number>; dependencies: { name: string; version: string; path: string }[];
  technologies: TechnologyEvidence[]; readme_excerpt: string;
  engineering_signals: { name: string; status: string; paths: string[] }[]; limitations: string[];
}
export interface SourceReceipt {
  url: string; status: string; detail: string; commit_sha?: string; fetched_at?: string;
  files_inspected?: number; files_omitted?: number; evidence_count?: number; ownership_score?: number;
  expanded_repositories?: string[];
  kind?: string; profile?: Record<string, string | number | null>; profile_error?: string;
  inventory?: { url: string; name: string; description: string | null; language: string | null; stars: number;
    fork: boolean; archived: boolean; pushed_at: string | null; inspection_status: string }[];
  inventory_truncated?: boolean; repository_review?: RepositoryReview;
  title?: string; description?: string; excerpt?: string; final_url?: string; http_status?: number;
  content_sha256?: string; verification?: string;
  acquisition_method?: string;
}
export interface SourceHealth {
  supplied_sources: number;
  observed_sources: number;
  failed_sources: number;
  not_selected_sources: number;
  not_scanned_sources: number;
  blocked_sources: number;
  is_partial: boolean;
  flags: string[];
}
export interface ComprehensiveAnalysis {
  method: string; coverage: { supplied_sources: number; observed_sources: number; skills_declared: number;
    skills_with_repository_matches: number; credential_claims: number };
  role_fit?: RoleFitSummary; analysis_confidence?: AnalysisConfidenceSummary; source_health?: SourceHealth;
  skills: { skill: string; learning: boolean; status: string; evidence: TechnologyEvidence[];
    evidence_count: number; public_mentions: string[]; explanation: string }[];
  credentials: { claim: string; status: string; explanation: string; matching_pages: {
    url: string; title: string; matched_terms: string[]; candidate_name_present: boolean }[] }[];
  projects: { title: string; description: string; source_urls: string[]; status: string; explanation: string }[];
  education: { claim: string; status: string }[]; experience: { claim: string; status: string }[];
  achievements: { claim: string; status: string }[]; quantified_claims_to_verify: string[]; next_steps: string[];
}
export interface LiveResult {
  intake: ResumeIntake; dossier: Dossier & { evidence_records: (Evidence & { provenance: Evidence['provenance'] & {
    artifact_sha256?: string; artifact_url?: string; symbol_or_line?: string;
  } })[] };
  sources: SourceReceipt[]; source_health?: SourceHealth; graph: CEGGraph; graph_snapshot: unknown; status: string;
  analysis: ComprehensiveAnalysis;
}

export const FALLBACK_ANALYSIS_CONFIDENCE: AnalysisConfidenceSummary = {
  evidence_strength: 'insufficient',
  explanation: 'The evidence-strength summary was not supplied; treat this analysis as insufficient until it is verified.',
  uncertainty_flags: ['confidence_summary_unavailable'],
  role_coverage: 0,
  observed_capabilities: 0,
  independent_clusters: 0,
  capabilities_with_intervals: 0,
  interval_coverage: 0,
  maximum_interval_width: null,
  meaningful_conflicts: 0,
  mandatory_unknown: 0,
  mandatory_unresolved: 0,
  source_failures: 0,
  source_unscanned: 0,
  unusable_evidence_records: 0,
};

const EVIDENCE_STRENGTHS = new Set<AnalysisConfidenceSummary['evidence_strength']>([
  'insufficient', 'limited', 'moderate', 'well_supported',
]);

export function getAnalysisConfidence(
  dossier: Dossier,
  analysis?: Pick<ComprehensiveAnalysis, 'analysis_confidence'>,
): AnalysisConfidenceSummary {
  const confidence = dossier.analysis_confidence ?? analysis?.analysis_confidence;
  if (!confidence || !EVIDENCE_STRENGTHS.has(confidence.evidence_strength)) {
    return FALLBACK_ANALYSIS_CONFIDENCE;
  }
  return confidence;
}

export function getSourceHealth(result: Pick<LiveResult, 'sources' | 'source_health' | 'analysis'>): SourceHealth {
  if (result.source_health) return result.source_health;
  if (result.analysis.source_health) return result.analysis.source_health;
  const statuses = result.sources.map(source => source.status);
  const observed = statuses.filter(status => status === 'observed').length;
  const notSelected = statuses.filter(status => status === 'not_selected').length;
  const notScanned = statuses.filter(status => status === 'not_scanned').length;
  const blocked = statuses.filter(status => status === 'security_blocked').length;
  const failed = statuses.filter(status => !['observed', 'not_selected', 'not_scanned'].includes(status)).length;
  const flags = [
    ...(failed ? ['source_failures'] : []),
    ...(notSelected || notScanned ? ['source_unscanned'] : []),
    ...(blocked ? ['security_blocked'] : []),
    ...(statuses.length === 0 ? ['no_sources_supplied'] : []),
  ];
  return {
    supplied_sources: statuses.length,
    observed_sources: observed,
    failed_sources: failed,
    not_selected_sources: notSelected,
    not_scanned_sources: notScanned,
    blocked_sources: blocked,
    is_partial: Boolean(failed || notSelected || notScanned || !observed),
    flags,
  };
}
export async function liveRequest<T>(operation: string, body: BodyInit, filename?: string): Promise<T> {
  const response = await fetch(`/api/live/${operation}`, { method: 'POST', body,
    headers: filename ? { 'X-Filename': encodeURIComponent(filename) } : { 'Content-Type': 'application/json' } });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed. Check the document and links.');
  return data as T;
}
export function publicUrl(value?: string): string | undefined {
  if (!value) return undefined;
  try { const parsed = new URL(value); return ['https:', 'http:'].includes(parsed.protocol) && !parsed.username && !parsed.password ? value : undefined; }
  catch { return undefined; }
}
