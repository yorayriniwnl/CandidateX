'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import type { CanonicalRole } from '../../types/cci';
import { liveRequest, publicUrl, type LiveResult, type ResumeIntake } from '../../lib/live-analysis';
import { AnalysisWizard } from './AnalysisWizard';
import { LiveDossier } from './LiveDossier';
import type { EvaluationStep } from './EvaluationSteps';
import type { SourceSelection } from './SourceManifestStep';
import styles from './evidence-os.module.css';

type Phase = 'idle' | 'upload' | 'analyze';

function sourceCategory(url: string, category: string) {
  if (category === 'github_urls') {
    try {
      const path = new URL(url).pathname.split('/').filter(Boolean);
      return path.length > 1 ? 'GitHub repository' : 'GitHub profile';
    } catch { return 'GitHub source'; }
  }
  const labels: Record<string, string> = {
    linkedin_urls: 'LinkedIn',
    coding_profile_urls: 'Coding profile',
    credential_urls: 'Credential page',
    deployment_urls: 'Deployment',
    portfolio_urls: 'Portfolio',
    project_links: 'Project link',
  };
  return labels[category] ?? 'Public source';
}

function sourceSelections(intake: ResumeIntake): SourceSelection[] {
  const groups: [string, string[]][] = [
    ['github_urls', intake.manifest.github_urls],
    ['linkedin_urls', intake.manifest.linkedin_urls],
    ['coding_profile_urls', intake.manifest.coding_profile_urls],
    ['credential_urls', intake.manifest.credential_urls],
    ['deployment_urls', intake.manifest.deployment_urls],
    ['portfolio_urls', intake.manifest.portfolio_urls],
    ['project_links', intake.manifest.project_links],
  ];
  const seen = new Set<string>();
  return groups.flatMap(([group, urls]) => {
    const selections: SourceSelection[] = [];
    for (const url of urls) {
      const normalized = url.trim();
      const key = normalized.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      const selectable = Boolean(publicUrl(normalized));
      selections.push({
        url: normalized,
        kind: group === 'github_urls' ? 'github' : 'public',
        category: sourceCategory(normalized, group),
        declared: true,
        selectable,
        selected: selectable,
        reason: selectable ? undefined : 'Only credential-free HTTP or HTTPS URLs can be submitted.',
      });
    }
    return selections;
  });
}

function declaredGithubIdentity(intake: ResumeIntake): string {
  const profile = intake.manifest.github_urls.find(url => {
    try { return new URL(url).pathname.split('/').filter(Boolean).length === 1; } catch { return false; }
  });
  if (!profile) return '';
  try { return new URL(profile).pathname.split('/').filter(Boolean)[0] ?? ''; } catch { return ''; }
}

export function LiveEvaluation() {
  const [intake, setIntake] = useState<ResumeIntake | null>(null);
  const [result, setResult] = useState<LiveResult | null>(null);
  const [role, setRole] = useState<CanonicalRole>('backend');
  const [jd, setJd] = useState('');
  const [sources, setSources] = useState<SourceSelection[]>([]);
  const [identity, setIdentity] = useState('');
  const [fileName, setFileName] = useState('');
  const [fileSize, setFileSize] = useState(0);
  const [error, setError] = useState('');
  const [sourceError, setSourceError] = useState('');
  const [phase, setPhase] = useState<Phase>('idle');
  const [step, setStep] = useState<EvaluationStep>(0);
  const [showWizard, setShowWizard] = useState(true);
  const [previousRunNotice, setPreviousRunNotice] = useState('');
  const busy = useRef(false);
  const isBusy = phase !== 'idle';

  async function upload(file?: File) {
    if (!file || busy.current) return;
    setError('');
    setSourceError('');
    if (!/\.(pdf|docx)$/i.test(file.name)) { setError('Choose a PDF or DOCX resume.'); return; }
    if (file.size > 3 * 1024 * 1024) { setError('Resume must be 3 MB or smaller.'); return; }
    busy.current = true;
    setPhase('upload');
    try {
      const parsed = await liveRequest<ResumeIntake>('intake', file, file.name);
      setIntake(parsed);
      setFileName(file.name);
      setFileSize(file.size);
      setSources(sourceSelections(parsed));
      setIdentity(declaredGithubIdentity(parsed));
      setStep(0);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Resume could not be parsed.');
    } finally {
      busy.current = false;
      setPhase('idle');
    }
  }

  function removeResume() {
    setIntake(null);
    setSources([]);
    setIdentity('');
    setFileName('');
    setFileSize(0);
    setError('');
    setStep(0);
  }

  function addSource(value: string) {
    setSourceError('');
    const url = value.trim();
    const existing = sources.find(source => source.url.toLowerCase() === url.toLowerCase());
    if (existing) {
      if (!existing.selectable) { setSourceError(existing.reason ?? 'This source cannot be submitted.'); return; }
      setSources(current => current.map(source => source.url.toLowerCase() === url.toLowerCase() ? { ...source, selected: true } : source));
      return;
    }

    const selectable = Boolean(publicUrl(url));
    let github = false;
    try { github = new URL(url).hostname.toLowerCase().replace(/^www\./, '') === 'github.com'; } catch { /* keep it visible as unsupported */ }
    let category = github ? sourceCategory(url, 'github_urls') : 'Public webpage';
    if (!selectable) category = 'Unsupported URL';
    const item: SourceSelection = {
      url,
      kind: github ? 'github' : 'public',
      category,
      declared: false,
      selectable,
      selected: selectable,
      reason: selectable ? undefined : 'Only credential-free HTTP or HTTPS URLs can be submitted.',
    };
    setSources(current => [...current, item]);
    if (!selectable) setSourceError(item.reason ?? 'This source cannot be submitted.');
  }

  function toggleSource(url: string, selected: boolean) {
    setSources(current => current.map(source => source.url === url ? { ...source, selected } : source));
  }

  async function analyze() {
    if (!intake || busy.current) return;
    busy.current = true;
    setPhase('analyze');
    setError('');
    setPreviousRunNotice('');
    const previousRunId = result?.dossier.analysis_run_id;
    try {
      const selected = sources.filter(source => source.selected && source.selectable);
      const data = await liveRequest<LiveResult>('analyze', JSON.stringify({
        intake,
        role,
        jd_text: jd,
        github_urls: selected.filter(source => source.kind === 'github').map(source => source.url),
        github_identity: identity.trim(),
        external_urls: selected.filter(source => source.kind === 'public').map(source => source.url),
      }));
      setResult(data);
      setShowWizard(false);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Analysis could not complete.';
      setError(message);
      if (previousRunId) {
        setPreviousRunNotice(`The previous dossier is still shown and belongs to run ${previousRunId}. This failed request did not replace it.`);
      }
    } finally {
      busy.current = false;
      setPhase('idle');
    }
  }

  function newEvaluation() {
    setIntake(null);
    setSources([]);
    setIdentity('');
    setFileName('');
    setFileSize(0);
    setRole('backend');
    setJd('');
    setError('');
    setSourceError('');
    setPreviousRunNotice('');
    setStep(0);
    setShowWizard(true);
  }

  return (
    <div className={`${styles.app} observatory-route observatory-route--live`}>
      <header className={styles.appHeader}>
        <Link href="/" className={styles.appBrand} aria-label="CandidateX home">
          <span className={styles.appMark} aria-hidden="true">CX</span>
          <span>CandidateX</span>
        </Link>
        <div className={styles.appHeaderMeta}>
          <span>LIVE EVIDENCE / ANALYSIS</span>
          <Link href="/research-demo">Research demo <span aria-hidden="true">↗</span></Link>
        </div>
      </header>
      <main className={styles.appBody}>
        {showWizard && <AnalysisWizard
          step={step}
          intake={intake}
          fileName={fileName}
          fileSize={fileSize}
          role={role}
          jd={jd}
          sources={sources}
          identity={identity}
          busy={isBusy}
          phase={phase}
          error={error}
          sourceError={sourceError}
          previousRun={result}
          onStepChange={setStep}
          onUpload={upload}
          onRemoveResume={removeResume}
          onRoleChange={setRole}
          onJdChange={setJd}
          onToggleSource={toggleSource}
          onAddSource={addSource}
          onIdentityChange={setIdentity}
          onAnalyze={analyze}
        />}

        {previousRunNotice && <div className={styles.previousRunNotice} role="status" aria-live="polite">{previousRunNotice}</div>}
        {result && <LiveDossier key={result.dossier.analysis_run_id} result={result} onNewEvaluation={newEvaluation} />}
      </main>

      <footer className={styles.appFooter}>
        <span>CandidateX · Research-informed technical decision support. Export the dossier to keep it; this page does not retain resumes or results across refreshes.</span>
        <span>Resume identity and account association are declarations; static observations do not verify mastery or job performance. Live resumes and results are request-scoped.</span>
      </footer>
    </div>
  );
}
