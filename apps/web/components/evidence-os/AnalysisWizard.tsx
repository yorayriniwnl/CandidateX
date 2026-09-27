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
import { Instrument } from '../studio/Instrument';
import { ArrowUpRight, Check, FileText, GitBranch, Layers3, MessageSquare } from 'lucide-react';

const CONTEXT = [
  ['Potential starts with context.', 'A document is the beginning of a story. Let the work behind it bring the person into focus.'],
  ['One person. The right lens.', 'Choose the role that gives the evidence meaning. The same work can tell a different story in a different context.'],
  ['Follow the work to its source.', 'Choose the artifacts worth exploring. Keep declarations, observations, and unanswered questions distinct.'],
  ['A clearer view starts here.', 'Your inputs become a connected evidence trail, with capability signals and questions for the conversation ahead.'],
];

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
          <p>Bring the context. Connect the evidence. Prepare a sharper interview.</p>
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

      {step === 0 && <ResumeStep intake={intake} fileName={fileName} fileSize={fileSize} busy={busy} onUpload={onUpload} onRemove={onRemoveResume} onContinue={onStepChange} />}
      {step === 1 && <RoleStep role={role} jd={jd} busy={busy} onRoleChange={onRoleChange} onJdChange={onJdChange} onContinue={onStepChange} />}
      {step === 2 && <SourceManifestStep sources={sources} identity={identity} busy={busy} addError={sourceError} onToggle={onToggleSource} onAdd={onAddSource} onIdentityChange={onIdentityChange} onContinue={onStepChange} />}
      {step === 3 && <ReviewStep role={role} jd={jd} sources={sources} busy={busy} onContinue={onStepChange} onAnalyze={onAnalyze} />}
      </div>
      <aside className={styles.guide} aria-label="Evaluation context">
        <div className={styles.guideTop}><span>CX / EVIDENCE ENGINE</span><span>0{step + 1} — 04</span></div>
        <Instrument stage={step} />
        <div className={styles.guideCopy}><p className={styles.sectionEyebrow}>INTELLIGENCE, MADE TRACEABLE</p><h2>{CONTEXT[step][0]}</h2><p>{CONTEXT[step][1]}</p></div>
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
