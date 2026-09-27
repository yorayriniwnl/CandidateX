import { humanStatus } from './format';
import styles from './evidence-os.module.css';

export type StatusTone = 'observed' | 'incomplete' | 'conflict' | 'unknown' | 'neutral';

export function statusTone(value: string): StatusTone {
  const status = value.toLowerCase();
  if (/conflict|contradict|failed|error|security_blocked/.test(status)) return 'conflict';
  if (/unknown|not_observed|pending|none/.test(status)) return 'unknown';
  if (/unsupported|ownership_uncertain/.test(status)) return 'incomplete';
  if (/observed|corroborated|completed|success|supported|supporting|repository_support/.test(status)) return 'observed';
  if (/partial|not_selected|unverified|possible_public_match|restricted|unsupported|omitted|not_scanned|unavailable|repository_only|public_mention_only|linked_sources|declaration_only/.test(status)) return 'incomplete';
  return 'neutral';
}

export function EvidenceStatus({ status, tone, label, explanation }: { status: string; tone?: StatusTone; label?: string; explanation?: string }) {
  const selectedTone = tone ?? statusTone(status);
  return (
    <span title={explanation} tabIndex={explanation ? 0 : undefined} aria-label={explanation ? `${label ?? humanStatus(status)}: ${explanation}` : undefined} className={`${styles.status} ${styles[`status_${selectedTone}`]}`}>
      <span className={styles.statusDot} aria-hidden="true" />
      {label ?? humanStatus(status)}
    </span>
  );
}
