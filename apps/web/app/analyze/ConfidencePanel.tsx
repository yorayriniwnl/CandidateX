import type { EvidenceStrength } from '../../types/cci';
import { getAnalysisConfidence, getSourceHealth, type LiveResult } from '../../lib/live-analysis';
import { label } from '../../lib/evidence';
import styles from './shared.module.css';

const STRENGTH_LABELS: Record<EvidenceStrength, string> = {
  insufficient: 'Insufficient evidence',
  limited: 'Limited support',
  moderate: 'Moderate support',
  well_supported: 'Well supported within supplied evidence',
};

const FLAG_LABELS: Record<string, string> = {
  confidence_summary_unavailable: 'Evidence-strength summary unavailable',
  no_empirical_evidence: 'No empirical evidence',
  low_role_coverage: 'Low role coverage',
  single_cluster: 'Single independent cluster',
  interval_unavailable: 'Confidence interval unavailable',
  wide_intervals: 'Wide confidence interval',
  mandatory_unknown: 'Mandatory requirement is unknown',
  mandatory_unresolved: 'Mandatory requirement is unresolved',
  source_failures: 'Source acquisition failures',
  source_unscanned: 'Sources were not scanned or selected',
  security_blocked: 'Source blocked by security policy',
  meaningful_conflict: 'Meaningful evidence conflict',
  unusable_evidence: 'Unusable evidence retained',
  no_sources_supplied: 'No sources supplied',
};

function percentage(value: number) {
  return `${Math.round(value * 100)}%`;
}

function flagLabel(flag: string) {
  return FLAG_LABELS[flag] ?? label(flag);
}

export function EvidenceStrengthPanel({ result }: { result: LiveResult }) {
  const confidence = getAnalysisConfidence(result.dossier);
  const sourceHealth = getSourceHealth(result);
  const flags = [...new Set([...confidence.uncertainty_flags, ...sourceHealth.flags])];

  return <section className={`${styles.panel} ${styles.confidencePanel}`} aria-label="Evidence strength">
    <div className={styles.eyebrow}>Evidence strength / uncertainty</div>
    <div className={styles.confidenceHeader}>
      <div>
        <h2>Evidence strength</h2>
        <p className={styles.confidenceExplanation}>{confidence.explanation}</p>
      </div>
      <span className={`${styles.statusPill} ${confidence.evidence_strength === 'well_supported' ? styles.statusGood : styles.statusNeedsReview}`}>
        {STRENGTH_LABELS[confidence.evidence_strength]}
      </span>
    </div>
    <p className={styles.confidenceBoundary}>This is not a probability or hiring recommendation. It describes how much support the supplied evidence provides; unknown capabilities stay unknown.</p>
    <div className={styles.confidenceMetrics}>
      <div className={styles.confidenceMetric}><span>Role coverage</span><strong>{percentage(confidence.role_coverage)}</strong><small>weighted observed evidence</small></div>
      <div className={styles.confidenceMetric}><span>Observed capabilities</span><strong>{confidence.observed_capabilities} / 12</strong><small>with a usable estimate</small></div>
      <div className={styles.confidenceMetric}><span>Independent clusters</span><strong>{confidence.independent_clusters}</strong><small>separate project or source groups</small></div>
      <div className={styles.confidenceMetric}><span>Intervals available</span><strong>{confidence.capabilities_with_intervals}</strong><small>{percentage(confidence.interval_coverage)} of observed role weight</small></div>
      <div className={styles.confidenceMetric}><span>Source health</span><strong>{sourceHealth.observed_sources} / {sourceHealth.supplied_sources}</strong><small>{sourceHealth.failed_sources} failed · {sourceHealth.not_scanned_sources + sourceHealth.not_selected_sources} unscanned</small></div>
    </div>
    <div className={styles.uncertaintyList}>
      <div><strong>What still limits this read</strong><span>Review these before treating an observed score as broadly supported.</span></div>
      <ul>
        {flags.length > 0 ? flags.map(flag => <li key={flag}>{flagLabel(flag)}</li>) : <li>No additional flags were reported; this still covers supplied evidence only.</li>}
      </ul>
    </div>
  </section>;
}
