import type { CapabilityKey } from '../types/cci';

export const SOURCES = ['resume', 'github', 'deployment', 'database', 'coding', 'certificate', 'linkedin'] as const;
export type Source = typeof SOURCES[number];

export interface Evidence {
  evidence_id: string;
  fingerprint: string;
  source_family: Source;
  source_locator: string;
  immutable_revision: string;
  target_capability: CapabilityKey;
  support_score: number;
  is_positive_support: boolean;
  confidence: number;
  cluster_id: string | null;
  confidence_factors: Record<string, number>;
  provenance: {
    artifact_path: string;
    raw_support_text: string;
    extractor_version: string;
    verification_status: string;
    observed_at: string;
  };
}

export function label(value: string) {
  return value.replaceAll('_', ' ');
}
