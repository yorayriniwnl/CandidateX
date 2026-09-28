import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence, type Variants } from 'framer-motion';
import type { CanonicalRole } from '../../types/cci';
import type { LiveResult, ResumeIntake } from '../../lib/live-analysis';
import { AnalysisRunStatus } from './AnalysisRunStatus';
import { PendingAnalysisSkeleton } from './PendingAnalysisSkeleton';
import { EvaluationSteps, type EvaluationStep } from './EvaluationSteps';
import { ResumeStep } from './ResumeStep';
import { RoleStep } from './RoleStep';
import { SourceManifestStep, type SourceSelection } from './SourceManifestStep';
import { ReviewStep } from './ReviewStep';
import Link from 'next/link';
import styles from './evidence-os.module.css';
import { Instrument } from '../studio/Instrument';
import { ArrowUpRight, Check, FileText, GitBranch, Home, Layers3, MessageSquare, Users } from 'lucide-react';

const CONTEXT = [
  ['Potential starts with context.', 'A document is the beginning of a story. Let the work behind it bring the person into focus.'],
  ['One person. The right lens.', 'Choose the role that gives the evidence meaning. The same work can tell a different story in a different context.'],
  ['Follow the work to its source.', 'Choose the artifacts worth exploring. Keep declarations, observations, and unanswered questions distinct.'],
  ['A clearer view starts here.', 'Your inputs become a connected evidence trail, with capability signals and questions for the conversation ahead.'],
];

const stepVariants: Variants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 32 : -32,
    opacity: 0,
    filter: 'blur(2px)',
  }),
  center: {
    x: 0,
    opacity: 1,
    filter: 'blur(0px)',
    transition: {
      duration: 0.35,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -32 : 32,
    opacity: 0,
    filter: 'blur(2px)',
    transition: {
      duration: 0.22,
      ease: [0.16, 1, 0.3, 1],
    },
  }),
};

export function AnalysisWizard({
  step,
  intake,
  fileName,
  fileSize,
  role,
  jd,
  jdFileName,
  jdFileSize,
  jdLoading,
  jdError,
  jdWarning,
  sources,
  identity,
  busy,
  phase,
  error,
  sourceError,
  previousRun,
  onStepChange,
  onUpload,
  onRemoveResume,
  onRoleChange,
  onJdChange,
  onJdUpload,
  onJdRemove,
  onToggleSource,
  onAddSource,
  onIdentityChange,
  onAnalyze,
  onFetchLink,
  onFetchAllCloud,
}: {
  step: EvaluationStep;
  intake: ResumeIntake | null;
  fileName: string;
  fileSize: number;
  role: CanonicalRole;
  jd: string;
  jdFileName?: string;
  jdFileSize?: number;
  jdLoading?: boolean;
  jdError?: string;
  jdWarning?: string;
  sources: SourceSelection[];
  identity: string;
  busy: boolean;
  phase: 'idle' | 'upload' | 'analyze';
  error: string;
  sourceError: string;
  previousRun: LiveResult | null;
  onStepChange: (step: EvaluationStep) => void;
  onUpload: (file?: File) => void;
  onRemoveResume: () => void;
  onRoleChange: (role: CanonicalRole) => void;
  onJdChange: (jd: string) => void;
  onJdUpload?: (file?: File) => void;
  onJdRemove?: () => void;
  onToggleSource: (url: string, selected: boolean) => void;
  onAddSource: (url: string) => void;
  onIdentityChange: (identity: string) => void;
  onAnalyze: () => void;
  onFetchLink?: (url: string) => void;
  onFetchAllCloud?: () => void;
}) {
  const maximumStep = intake ? 3 : 0;
  const [direction, setDirection] = useState(1);
  const prevStepRef = useRef(step);

  useEffect(() => {
    if (step !== prevStepRef.current) {
      setDirection(step > prevStepRef.current ? 1 : -1);
      prevStepRef.current = step;
    }
  }, [step]);

  return (
    <section className={styles.wizard} aria-labelledby="evaluation-title">
      <div className={styles.pageHeading}>
        <div>
          <p className={styles.kicker}>NEW EVALUATION / LIVE</p>
          <h1 id="evaluation-title">Build a candidate dossier.</h1>
          <p>Bring the context. Connect the evidence. Prepare a sharper interview.</p>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginTop: '14px', flexWrap: 'wrap' }}>
            <Link
              href="/hr"
              scroll={true}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 14px',
                borderRadius: '7px',
                background: '#ffffff05',
                border: '1px solid #ad8ecd39',
                color: '#d4dbe6',
                fontSize: '12px',
                textDecoration: 'none',
              }}
              title="Land to Candidates"
              data-testid="wizard-landing-btn-candidates"
            >
              <Users size={13} aria-hidden="true" />
              Candidates
            </Link>
            <Link
              href="/"
              scroll={true}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 14px',
                borderRadius: '7px',
                background: '#ffffff05',
                border: '1px solid #ad8ecd39',
                color: '#d4dbe6',
                fontSize: '12px',
                textDecoration: 'none',
              }}
              title="Land to Home"
              data-testid="wizard-landing-btn-home"
            >
              <Home size={13} aria-hidden="true" />
              Home
            </Link>
          </div>
        </div>
        {previousRun && <div className={styles.previousRun} role="status">
          <span>LAST COMPLETED RUN</span><code>{previousRun.dossier.analysis_run_id}</code>
          <p>Retained until a new analysis succeeds.</p>
        </div>}
      </div>

      <EvaluationSteps active={step} canAdvanceTo={maximumStep} busy={busy} onChange={onStepChange} />
      <div className={styles.wizardLayout}>
      <div className={styles.wizardMain}>
      {error && <div className={styles.errorBanner} role="alert"><strong>Request not completed</strong><span>{error}</span></div>}
      {phase !== 'idle' && <AnalysisRunStatus phase={phase} />}
      {phase === 'analyze' && !previousRun && <PendingAnalysisSkeleton />}

      <AnimatePresence mode="wait" custom={direction}>
        <motion.div
          key={step}
          custom={direction}
          variants={stepVariants}
          initial="enter"
          animate="center"
          exit="exit"
          style={{ width: '100%' }}
        >
          {step === 0 && (
            <ResumeStep
              intake={intake}
              fileName={fileName}
              fileSize={fileSize}
              busy={busy}
              onUpload={onUpload}
              onRemove={onRemoveResume}
              onContinue={onStepChange}
            />
          )}
          {step === 1 && (
            <RoleStep
              role={role}
              jd={jd}
              jdFileName={jdFileName}
              jdFileSize={jdFileSize}
              jdLoading={jdLoading}
              jdError={jdError}
              jdWarning={jdWarning}
              busy={busy}
              onRoleChange={onRoleChange}
              onJdChange={onJdChange}
              onJdUpload={onJdUpload}
              onJdRemove={onJdRemove}
              onContinue={onStepChange}
            />
          )}
          {step === 2 && (
            <SourceManifestStep
              sources={sources}
              identity={identity}
              busy={busy}
              addError={sourceError}
              onToggle={onToggleSource}
              onAdd={onAddSource}
              onIdentityChange={onIdentityChange}
              onContinue={onStepChange}
              onFetchLink={onFetchLink}
              onFetchAllCloud={onFetchAllCloud}
            />
          )}
          {step === 3 && (
            <ReviewStep
              role={role}
              jd={jd}
              jdFileName={jdFileName}
              sources={sources}
              busy={busy}
              onContinue={onStepChange}
              onAnalyze={onAnalyze}
            />
          )}
        </motion.div>
      </AnimatePresence>
      </div>
      <aside className={styles.guide} aria-label="Evaluation context">
        <div className={styles.guideTop}><span>CX / EVIDENCE ENGINE</span><span>0{step + 1} — 04</span></div>
        <Instrument stage={step} />
        <div className={styles.guideCopy}>
          <p className={styles.sectionEyebrow}>INTELLIGENCE, MADE TRACEABLE</p>
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
            >
              <h2>{CONTEXT[step][0]}</h2>
              <p>{CONTEXT[step][1]}</p>
            </motion.div>
          </AnimatePresence>
        </div>
        <div className={styles.guideManifest}>
          <div><FileText size={13} aria-hidden="true" /><span>Candidate context</span><strong>{intake ? 'Supplied' : 'Awaiting résumé'}</strong>{intake && <Check size={12} aria-hidden="true" />}</div>
          <div><Layers3 size={13} aria-hidden="true" /><span>Role lens</span><strong>{role.replaceAll('_', ' ')}</strong></div>
          <div><GitBranch size={13} aria-hidden="true" /><span>Public sources</span><strong>{sources.filter(source => source.selected && source.selectable).length} selected</strong></div>
          <div><MessageSquare size={13} aria-hidden="true" /><span>Final judgment</span><strong>Always human</strong></div>
        </div>
        <a className={styles.guideLink} href="/research-demo">Explore the methodology <ArrowUpRight size={12} aria-hidden="true" /></a>
      </aside>
      </div>
    </section>
  );
}
