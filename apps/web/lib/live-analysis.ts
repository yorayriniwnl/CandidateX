import type { CEGGraph, Dossier } from '../types/cci';
import type { Evidence } from './research-demo';

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
  discovered_links?: { url: string; kind: string; discovery_reason: string }[];
}
export interface ComprehensiveAnalysis {
  method: string; coverage: { supplied_sources: number; observed_sources: number; skills_declared: number;
    skills_with_repository_matches: number; credential_claims: number };
  source_coverage?: { by_status: Record<string, number>; by_kind: Record<string, number>; discovered_links: number };
  discovered_links?: { url: string; kind: string; discovery_reason: string }[];
  claims?: { claim_id: string; category: string; claim: string; source: string; section: string;
    status: string; is_quantified: boolean; normalized_subject?: string; project_title?: string }[];
  academic_records?: { record_id: string; raw_claim: string; status: string; degree_text: string | null;
    years: string[]; claimed_cgpa: { value: number; scale: number | null } | null;
    claimed_percentage: number | null; evidence_sources: string[]; limitations: string[] }[];
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
  sources: SourceReceipt[]; graph: CEGGraph; graph_snapshot: unknown; status: string;
  analysis: ComprehensiveAnalysis;
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
