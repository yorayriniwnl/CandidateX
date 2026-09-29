export type FeatureFlagKey =
  | 'enable_3d_graph'
  | 'enable_ai_contradictions'
  | 'enable_pdf_export'
  | 'enable_team_roster'
  | 'enable_ablation_benchmarks';

const DEFAULT_FLAGS: Record<FeatureFlagKey, boolean> = {
  enable_3d_graph: true,
  enable_ai_contradictions: true,
  enable_pdf_export: true,
  enable_team_roster: true,
  enable_ablation_benchmarks: true,
};

export function isFeatureEnabled(flag: FeatureFlagKey): boolean {
  if (typeof window !== 'undefined') {
    try {
      const override = localStorage.getItem(`cx_flag_${flag}`);
      if (override !== null) {
        return override === 'true';
      }
    } catch {}
  }
  return DEFAULT_FLAGS[flag] ?? false;
}

export function setFeatureFlagOverride(flag: FeatureFlagKey, enabled: boolean): void {
  if (typeof window !== 'undefined') {
    try {
      localStorage.setItem(`cx_flag_${flag}`, String(enabled));
      window.dispatchEvent(new Event('cx-flags-changed'));
    } catch {}
  }
}
