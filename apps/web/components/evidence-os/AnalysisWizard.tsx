import type { CanonicalRole } from '../../types/cci';
import type { LiveResult, ResumeIntake } from '../../lib/live-analysis';
import { AnalysisRunStatus } from './AnalysisRunStatus';
import { PendingAnalysisSkeleton } from './PendingAnalysisSkeleton';
import { EvaluationSteps, type EvaluationStep } from './EvaluationSteps';
import { ResumeStep } from './ResumeStep';
import { RoleStep } from './RoleStep';
import { SourceManifestStep, type SourceSelection } from './SourceManifestStep';
import { ReviewStep } from './ReviewStep';
import styles from './evidence-os.module.css';

export function AnalysisWizard({ step, intake, fileName, fileSize, role, jd, sources, identity, busy, phase, error, sourceError, previousRun, onStepChange, onUpload, onRemoveResume, onRoleChange, onJdChange, onToggleSource, onAddSource, onIdentityChange, onAnalyze }: {
  step: EvaluationStep;
  intake: ResumeIntake | null;
  fileName: string;
  fileSize: number;
  role: CanonicalRole;
  jd: string;
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
  onToggleSource: (url: string, selected: boolean) => void;
  onAddSource: (url: string) => void;
  onIdentityChange: (identity: string) => void;
  onAnalyze: () => void;
}) {
  const maximumStep = intake ? 3 : 0;

  return (
    <section className={styles.wizard} aria-labelledby="evaluation-title">
      <div className={styles.pageHeading}>
        <div>
          <p className={styles.kicker}>NEW EVALUATION / LIVE</p>
          <h1 id="evaluation-title">Build a candidate dossier.</h1>
          <p>Review the declared inputs, choose public sources, then run bounded static analysis.</p>
        </div>
        {previousRun && <div className={styles.previousRun} role="status">
          <span>LAST COMPLETED RUN</span><code>{previousRun.dossier.analysis_run_id}</code>
          <p>Retained until a new analysis succeeds.</p>
        </div>}
      </div>

      <EvaluationSteps active={step} canAdvanceTo={maximumStep} busy={busy} onChange={onStepChange} />
      {error && <div className={styles.errorBanner} role="alert"><strong>Request not completed</strong><span>{error}</span></div>}
      {phase !== 'idle' && <AnalysisRunStatus phase={phase} />}
      {phase === 'analyze' && !previousRun && <PendingAnalysisSkeleton />}

      {step === 0 && <ResumeStep intake={intake} fileName={fileName} fileSize={fileSize} busy={busy} onUpload={onUpload} onRemove={onRemoveResume} onContinue={onStepChange} />}
      {step === 1 && <RoleStep role={role} jd={jd} busy={busy} onRoleChange={onRoleChange} onJdChange={onJdChange} onContinue={onStepChange} />}
      {step === 2 && <SourceManifestStep sources={sources} identity={identity} busy={busy} addError={sourceError} onToggle={onToggleSource} onAdd={onAddSource} onIdentityChange={onIdentityChange} onContinue={onStepChange} />}
      {step === 3 && <ReviewStep role={role} jd={jd} sources={sources} busy={busy} onContinue={onStepChange} onAnalyze={onAnalyze} />}
    </section>
  );
}
