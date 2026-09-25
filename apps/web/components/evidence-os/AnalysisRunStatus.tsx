import styles from './evidence-os.module.css';

export function AnalysisRunStatus({ phase }: { phase: 'upload' | 'analyze' }) {
  return (
    <div className={styles.runStatus} role="status" aria-live="polite" aria-busy="true">
      <span className={styles.runSpinner} aria-hidden="true" />
      <div>
        <strong>{phase === 'upload' ? 'Reading the resume' : 'Waiting for the live analysis response'}</strong>
        <p>{phase === 'upload'
          ? 'Extracting text and candidate-declared links from the supplied document.'
          : 'Analysis runs synchronously. The request can take up to 55 seconds; no backend stage progress is available.'}</p>
      </div>
    </div>
  );
}
