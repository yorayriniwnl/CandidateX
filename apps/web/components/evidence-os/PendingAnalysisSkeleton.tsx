import styles from './evidence-os.module.css';

export function PendingAnalysisSkeleton() {
  return (
    <div className={styles.pendingSkeleton} data-testid="pending-analysis-skeleton" aria-hidden="true">
      <div className={styles.skeletonHeading}>
        <span className={styles.skeletonLine} />
        <span className={styles.skeletonLine} />
      </div>
      <div className={styles.skeletonMetrics}>
        <span className={styles.skeletonMetric} />
        <span className={styles.skeletonMetric} />
        <span className={styles.skeletonMetric} />
        <span className={styles.skeletonMetric} />
      </div>
      <div className={styles.skeletonBody}>
        <div className={styles.skeletonSection}>
          <span className={styles.skeletonSectionTitle} />
          {Array.from({ length: 4 }, (_, index) => <span key={index} className={styles.skeletonCapabilityRow} />)}
        </div>
        <div className={styles.skeletonSection}>
          <span className={styles.skeletonSectionTitle} />
          {Array.from({ length: 3 }, (_, index) => <span key={index} className={styles.skeletonEvidenceRow} />)}
        </div>
      </div>
    </div>
  );
}
