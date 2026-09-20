import type { CEGGraph, Dossier } from '../types/cci';
import type { Evidence } from './research-demo';

export interface ResumeIntake {
  candidate_id: string;
  manifest: {
    display_name: string; email: string | null; claimed_skills: string[];
    github_urls: string[]; linkedin_urls: string[]; coding_profile_urls: string[];
    credential_urls: string[]; deployment_urls: string[]; portfolio_urls: string[]; project_links: string[];
  };
  filename: string; document_sha256: string; text_preview: string; warnings: string[]; storage: string;
}
export interface SourceReceipt {
  url: string; status: string; detail: string; commit_sha?: string; fetched_at?: string;
  files_inspected?: number; files_omitted?: number; evidence_count?: number; ownership_score?: number;
  expanded_repositories?: string[];
}
export interface LiveResult {
  intake: ResumeIntake; dossier: Dossier & { evidence_records: (Evidence & { provenance: Evidence['provenance'] & {
    artifact_sha256?: string; artifact_url?: string; symbol_or_line?: string;
  } })[] };
  sources: SourceReceipt[]; graph: CEGGraph; graph_snapshot: unknown; status: string;
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
