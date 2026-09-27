'use client';

import type { CanonicalRole } from '../../types/cci';
import { roleName } from './format';
import type { EvaluationStep } from './EvaluationSteps';
import styles from './evidence-os.module.css';

const ROLES: CanonicalRole[] = ['backend', 'frontend', 'fullstack', 'ml_engineer', 'devops_cloud', 'data_engineer'];

export function RoleStep({ role, jd, busy, onRoleChange, onJdChange, onContinue }: {
  role: CanonicalRole;
  jd: string;
  busy: boolean;
  onRoleChange: (role: CanonicalRole) => void;
  onJdChange: (jd: string) => void;
  onContinue: (step: EvaluationStep) => void;
}) {
  return (
    <section className={styles.stepPanel} aria-labelledby="role-step-title">
      <div className={styles.sectionEyebrow}>02 / Role context</div>
      <h2 id="role-step-title">Set the role context.</h2>
      <p className={styles.sectionIntro}>The role changes how observed evidence is organized. A job description is optional.</p>

      <div className={styles.roleControls}>
        <div className={styles.fieldBlock}>
          <label htmlFor="live-role">Target role</label>
          <select id="live-role" value={role} disabled={busy} onChange={event => onRoleChange(event.target.value as CanonicalRole)}>
            {ROLES.map(option => <option key={option} value={option}>{roleName(option)}</option>)}
          </select>
          <p>The role profile and weights are returned with the dossier after analysis.</p>
        </div>
        <div className={styles.fieldBlock}>
          <div className={styles.labelLine}>
            <label htmlFor="live-jd">Job description</label>
            <span>OPTIONAL</span>
          </div>
          <textarea
            id="live-jd"
            maxLength={20000}
            disabled={busy}
            placeholder="Paste the responsibilities and requirements…"
            value={jd}
            onChange={event => onJdChange(event.target.value)}
            rows={10}
          />
          <p>{jd.length.toLocaleString()} / 20,000 characters · Parsed during the analysis request.</p>
        </div>
      </div>
      <div className={styles.stepActions}>
        <button className={styles.secondaryButton} type="button" onClick={() => onContinue(0)}>← Resume</button>
        <button className={styles.primaryButton} type="button" onClick={() => onContinue(2)}>Continue to public sources <span aria-hidden="true">→</span></button>
      </div>
    </section>
  );
}
