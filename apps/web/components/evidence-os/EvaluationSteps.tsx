'use client';

import { motion } from 'framer-motion';
import styles from './evidence-os.module.css';

export const EVALUATION_STEPS = [
  'Resume',
  'Target role',
  'Public sources',
  'Review & analyze',
] as const;

export type EvaluationStep = 0 | 1 | 2 | 3;

export function EvaluationSteps({ active, canAdvanceTo, busy = false, onChange }: {
  active: EvaluationStep;
  canAdvanceTo: EvaluationStep;
  busy?: boolean;
  onChange: (step: EvaluationStep) => void;
}) {
  return (
    <nav aria-label="Evaluation steps" className={styles.stepper}>
      {EVALUATION_STEPS.map((label, index) => {
        const step = index as EvaluationStep;
        const complete = step < active;
        const isActive = step === active;
        const disabled = busy || step > canAdvanceTo;
        return (
          <button
            key={label}
            type="button"
            className={`${styles.step} ${isActive ? styles.stepActive : ''} ${complete ? styles.stepComplete : ''}`}
            aria-current={isActive ? 'step' : undefined}
            disabled={disabled}
            onClick={() => onChange(step)}
          >
            <span className={styles.stepNumber}>{String(index + 1).padStart(2, '0')}</span>
            <span>{label}</span>
            {isActive && (
              <motion.span
                layoutId="activeStepGlider"
                className={styles.stepActiveIndicator}
                transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              />
            )}
          </button>
        );
      })}
    </nav>
  );
}
