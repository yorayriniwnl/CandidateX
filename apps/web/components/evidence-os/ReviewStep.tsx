import type { CanonicalRole } from '../../types/cci';
import { roleName } from './format';
import type { EvaluationStep } from './EvaluationSteps';
import type { SourceSelection } from './SourceManifestStep';
import styles from './evidence-os.module.css';

export function ReviewStep({ role, jd, sources, busy, onContinue, onAnalyze }: {
  role: CanonicalRole;
  jd: string;
  sources: SourceSelection[];
  busy: boolean;
  onContinue: (step: EvaluationStep) => void;
  onAnalyze: () => void;
}) {
  const selected = sources.filter(source => source.selected && source.selectable);
  return (
    <section className={styles.stepPanel} aria-labelledby="review-step-title">
      <div className={styles.sectionEyebrow}>04 / Analysis request</div>
      <h2 id="review-step-title">Review analysis</h2>
      <p className={styles.sectionIntro}>Confirm the role and supplied sources before CandidateX starts the live request.</p>
      <dl className={styles.reviewGrid}>
        <div><dt>Target role</dt><dd>{roleName(role)}</dd></div>
        <div><dt>Job description</dt><dd>{jd.trim() ? `${jd.length.toLocaleString()} characters` : 'Not supplied'}</dd></div>
        <div><dt>Public source selection</dt><dd>{selected.length} public {selected.length === 1 ? 'source' : 'sources'} selected</dd></div>
        <div><dt>Analysis mode</dt><dd>Live static inspection · synchronous request</dd></div>
      </dl>
      {jd.trim() && <div className={styles.reviewText}><span>JOB DESCRIPTION PREVIEW</span><p>{jd.trim()}</p></div>}
      <div className={styles.reviewSources}>
        <h3>Sources selected for this request</h3>
        {selected.length === 0 ? <p>No public sources were selected for this run. Resume declarations alone do not establish capability.</p> : (
          <ul>{selected.map(source => <li key={`${source.kind}-${source.url}`}><span>{source.category}</span><code>{source.url}</code></li>)}</ul>
        )}
      </div>
      <div className={styles.runLimits}>
        The request is synchronous and may take up to 55 seconds. The interface will show the request state, not invented acquisition progress.
      </div>
      <div className={styles.stepActions}>
        <button className={styles.secondaryButton} type="button" disabled={busy} onClick={() => onContinue(2)}>← Public sources</button>
        <button className={styles.primaryButton} type="button" disabled={busy} onClick={onAnalyze}>
          {busy ? 'Waiting for analysis…' : 'Start live analysis'} <span aria-hidden="true">→</span>
        </button>
      </div>
    </section>
  );
}
