import type { CEGGraph, CapabilityKey, Dossier } from '../types/cci';

export const SOURCES = ['resume', 'github', 'deployment', 'database', 'coding', 'certificate', 'linkedin'] as const;
export type Source = typeof SOURCES[number];
export type Scenario = 'consistent' | 'sparse' | 'low_ownership' | 'conflicting' | 'empty';
export const SYNTHETIC_CANDIDATE_ID = 'd3333333-3333-4333-8333-333333333333';
export interface DemoInput {
  scenario: Scenario;
  role: Dossier['role'];
  excluded_sources: Source[];
  ownership_multiplier: number;
  reliability_false_positives: number;
}
export interface Evidence {
  evidence_id: string; fingerprint: string; source_family: Source; source_locator: string;
  immutable_revision: string; target_capability: CapabilityKey; support_score: number;
  is_positive_support: boolean; confidence: number; cluster_id: string | null;
  confidence_factors: Record<string, number>;
  provenance: { artifact_path: string; raw_support_text: string; extractor_version: string; verification_status: string; observed_at: string };
}
export interface ResearchDossier extends Dossier {
  evidence_records: Evidence[]; evidence_mode: string; scenario: Scenario;
  role_weights: Record<CapabilityKey, number>;
  override_history: { timestamp: string; justification: string; previous_dossier_id: string }[];
}
export interface DemoResult {
  dossier: ResearchDossier; graph: CEGGraph; graph_snapshot: unknown; input: DemoInput;
  evidence_digest: string; scenario_version: string;
  scoring_config: { low_coverage_threshold: number; temperature: number; probe_alpha: number; probe_beta: number; probe_gamma: number; tau_saturation: Record<CapabilityKey, number> };
  reliability: Record<Source, { alpha_prior: number; beta_prior: number; true_positive_count: number; false_positive_count: number; posterior_mean: number }>;
  stages: { label: string; status: string; details: string }[];
  benchmark_scope: { headline_reproduced: false; paper: { candidate_role_evaluations: number; spearman_rho: number; status: string }; prototype: { candidate_role_evaluations: number; spearman_rho_rounded: number; command: string; status: string } };
  storage_notice: string;
}

export async function demoRequest<T>(operation: 'run' | 'rescore', payload: unknown): Promise<T> {
  const response = await fetch('/api/demo', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ operation, payload }) });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Invalid demonstration input. Check the controls and try again.');
  return data as T;
}
export function label(value: string) { return value.replaceAll('_', ' '); }
