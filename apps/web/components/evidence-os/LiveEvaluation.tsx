'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchUserSession, isUserAuthenticated } from '../../lib/auth';
import type { CanonicalRole } from '../../types/cci';
import { liveRequest, publicUrl, fetchLinkData, type LiveResult, type ResumeIntake, type ParsedJobDescription } from '../../lib/live-analysis';
import { saveCandidateBackend } from '../../lib/api';
import { saveReviewToHR } from '../hr/hr-data';
import { normalizeTeamMember } from '../../lib/team-members';
import { PlatformHeader } from '../navigation/PlatformHeader';
import { AnalysisWizard } from './AnalysisWizard';
import { LiveDossier } from './LiveDossier';
import type { EvaluationStep } from './EvaluationSteps';
import type { SourceSelection } from './SourceManifestStep';
import { useEvaluationWorkflow } from './useEvaluationWorkflow';
import styles from './evidence-os.module.css';

type Phase = 'idle' | 'upload' | 'analyze';

function isCloudDrive(url: string): boolean {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return ['drive.google.com', 'docs.google.com', 'dropbox.com', 'onedrive.live.com', '1drv.ms', 'sharepoint.com', 'box.com', 'icloud.com'].some(d => host.includes(d));
  } catch {
    return false;
  }
}

function sourceCategory(url: string, category: string) {
  if (isCloudDrive(url)) {
    return 'Shared file (Drive/Cloud)';
  }
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
    shared_document_urls: 'Shared file (Drive/Cloud)',
    project_links: 'Project link',
    public_links: 'Public source',
  };
  return labels[category] ?? 'Public source';
}

function sourceSelections(intake: ResumeIntake): SourceSelection[] {
  const groups: [string, string[]][] = [
    ['github_urls', intake.manifest.github_urls || []],
    ['linkedin_urls', intake.manifest.linkedin_urls || []],
    ['coding_profile_urls', intake.manifest.coding_profile_urls || []],
    ['credential_urls', intake.manifest.credential_urls || []],
    ['deployment_urls', intake.manifest.deployment_urls || []],
    ['portfolio_urls', intake.manifest.portfolio_urls || []],
    ['shared_document_urls', intake.manifest.shared_document_urls || []],
    ['project_links', intake.manifest.project_links || []],
    ['public_links', intake.manifest.public_links || []],
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
  const router = useRouter();

  useEffect(() => {
    let active = true;

    // A valid HttpOnly session survives a fresh tab even when the client-side
    // display cache is empty. Resolve the server session before deciding that
    // the user is unauthenticated, otherwise protected routes can bounce valid
    // sessions back to /login during hydration.
    void fetchUserSession().then((user) => {
      if (active && !user) {
        router.replace('/login?redirect=/analyze');
      }
    });

    const handleAuthChange = () => {
      if (!isUserAuthenticated()) {
        router.replace('/login?redirect=/analyze');
      }
    };

    window.addEventListener('cx-auth-change', handleAuthChange);
    window.addEventListener('storage', handleAuthChange);
    return () => {
      active = false;
      window.removeEventListener('cx-auth-change', handleAuthChange);
      window.removeEventListener('storage', handleAuthChange);
    };
  }, [router]);

  const {
    state,
    dispatch,
    setIntake,
    setFileName,
    setFileSize,
    setRole,
    setJd,
    setBackendJdText,
    setBackendJobId,
    setJdFileName,
    setJdFileSize,
    setJdLoading,
    setJdError,
    setJdWarning,
    setSources,
    setIdentity,
    setStep,
    setPhase,
    setError,
    setSourceError,
    setShowWizard,
    setResult,
    setPreviousRunNotice,
    setHrSavedNotice,
  } = useEvaluationWorkflow();

  const {
    intake,
    result,
    role,
    jd,
    backendJdText,
    backendJobId,
    jdFileName,
    jdFileSize,
    jdLoading,
    jdError,
    jdWarning,
    sources,
    identity,
    fileName,
    fileSize,
    error,
    sourceError,
    phase,
    step,
    showWizard,
    previousRunNotice,
    hrSavedNotice,
  } = state;
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
      dispatch({
        type: 'RESUME_UPLOAD_SUCCESS',
        payload: {
          intake: parsed,
          fileName: file.name,
          fileSize: file.size,
          sources: sourceSelections(parsed),
          identity: declaredGithubIdentity(parsed),
        },
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Resume could not be parsed.');
      setPhase('idle');
    } finally {
      busy.current = false;
    }
  }

  function removeResume() {
    dispatch({ type: 'REMOVE_RESUME' });
  }

  async function uploadJd(file?: File) {
    if (!file || busy.current || jdLoading) return;
    setJdError('');
    setJdWarning('');
    const ext = file.name.toLowerCase();
    if (!/\.(pdf|docx|doc|txt|md)$/i.test(ext)) {
      setJdError('Choose a PDF, DOCX, DOC, or TXT document.');
      return;
    }
    if (file.size > 3 * 1024 * 1024) {
      setJdError('Document must be 3 MB or smaller.');
      return;
    }

    setJdLoading(true);
    try {
      if (ext.endsWith('.txt') || ext.endsWith('.md')) {
        const text = await file.text();
        const clean = text.trim();
        if (clean.length < 10) throw new Error('No readable text found in document.');
        const truncated = clean.length > 20000;
        setBackendJdText(clean.slice(0, 20000));
        setJd(clean.slice(0, 20000));
        setJdFileName(file.name);
        setJdFileSize(file.size);
        if (truncated) {
          setJdWarning('Document text was truncated to 20,000 characters to fit the analysis limit.');
        }
      } else {
        const parsed = await liveRequest<ParsedJobDescription & { job_id?: string }>('parse-jd', file, file.name);
        setBackendJdText(parsed.text || '');
        setJd(parsed.text || '');
        if (parsed.job_id) {
          setBackendJobId(parsed.job_id);
        }
        setJdFileName(parsed.filename || file.name);
        setJdFileSize(file.size);
        if (parsed.truncated) {
          setJdWarning('Document text was truncated to 20,000 characters to fit the analysis limit.');
        } else if (parsed.warnings && parsed.warnings.length > 0) {
          setJdWarning(parsed.warnings.join(' '));
        }
      }
    } catch (cause) {
      setJdError(cause instanceof Error ? cause.message : 'Document could not be read. Ensure it contains readable digital text.');
    } finally {
      setJdLoading(false);
    }
  }

  function removeJd() {
    dispatch({ type: 'REMOVE_JD' });
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

  async function fetchLink(url: string) {
    setSources(current => current.map(s => s.url.toLowerCase() === url.toLowerCase() ? { ...s, fetching: true, fetchError: undefined } : s));
    try {
      const data = await fetchLinkData(url);
      setSources(current => current.map(s => {
        if (s.url.toLowerCase() !== url.toLowerCase()) return s;
        const newCategory =
          data.inferred_kind === 'project'
            ? 'Project file (Fetched)'
            : data.inferred_kind === 'credential'
            ? 'Credential file (Fetched)'
            : data.inferred_kind === 'portfolio'
            ? 'Portfolio website (Fetched)'
            : 'Shared file (Fetched)';
        return {
          ...s,
          fetching: false,
          fetchedData: data,
          category: newCategory,
        };
      }));
    } catch (cause) {
      setSources(current => current.map(s => {
        if (s.url.toLowerCase() !== url.toLowerCase()) return s;
        return {
          ...s,
          fetching: false,
          fetchError: cause instanceof Error ? cause.message : 'Could not fetch link.',
        };
      }));
    }
  }

  async function fetchAllCloud() {
    const targets = sources.filter(s => isCloudDrive(s.url) && !s.fetchedData && !s.fetching);
    for (const target of targets) {
      fetchLink(target.url);
    }
  }

  async function analyze() {
    if (!intake || busy.current) return;
    busy.current = true;
    setPhase('analyze');
    setError('');
    setPreviousRunNotice('');
    setHrSavedNotice('');
    const previousRunId = result?.dossier.analysis_run_id;
    try {
      const selected = sources.filter(source => source.selected && source.selectable);
      const effectiveJd = jd.trim() || backendJdText;
      const data = await liveRequest<LiveResult>('analyze', JSON.stringify({
        intake,
        role,
        jd_text: effectiveJd,
        job_id: backendJobId || undefined,
        github_urls: selected.filter(source => source.kind === 'github').map(source => source.url),
        github_identity: identity.trim(),
        external_urls: selected.filter(source => source.kind === 'public').map(source => source.url),
      }));
      setResult(data);
      setShowWizard(false);

      // Auto-save candidate profile to HR at the end of the review
      try {
        const rawId = data.intake.candidate_id || data.dossier.candidate_id || crypto.randomUUID();
        const rawName = data.intake.manifest.display_name || 'Candidate';
        const rawEmail = data.intake.manifest.email || undefined;
        const candidateRole = data.dossier.role || role;

        const normalized = normalizeTeamMember({
          id: rawId,
          display_name: rawName,
          primary_email: rawEmail,
          role: candidateRole,
          role_label: '',
          has_completed_dossier: true,
          has_meaningful_conflict: false,
          created_at: '',
        });

        const candidateId = normalized.id;
        const candidateName = normalized.display_name;
        const candidateEmail = normalized.primary_email;
        const score = data.dossier.rci;
        const coverage = data.dossier.coverage;
        const hasConflict = data.dossier.capability_conflicts
          ? Object.values(data.dossier.capability_conflicts).some(item => item.has_meaningful_conflict)
          : false;

        const manifest = {
          candidate_id: candidateId,
          full_name: candidateName,
          primary_email: candidateEmail,
          picture: data.intake.manifest.picture || data.intake.picture || undefined,
          github_usernames: identity.trim() ? [identity.trim()] : [],
          github_repositories: selected.filter(s => s.kind === 'github').map(s => s.url),
          deployment_urls: [],
          portfolio_urls: selected.filter(s => s.kind === 'public').map(s => s.url),
          declared_skills: data.intake.manifest.claimed_skills || [],
          extraction_metadata: { source: 'live_review', role: candidateRole },
        };

        saveReviewToHR({
          candidateId,
          displayName: candidateName,
          email: candidateEmail,
          role: candidateRole,
          rci: score,
          coverage,
          hasMeaningfulConflict: hasConflict,
          manifest,
          dossier: data.dossier,
          graph: data.graph,
        });

        saveCandidateBackend({
          id: candidateId,
          display_name: candidateName,
          primary_email: candidateEmail,
          role: candidateRole,
          rci: score ?? undefined,
          coverage,
          has_meaningful_conflict: hasConflict,
          has_completed_dossier: true,
          created_at: data.dossier.generated_at || new Date().toISOString(),
          manifest,
        }).catch(() => {});

        setHrSavedNotice(`Candidate profile for ${candidateName} saved to HR with Score ${score != null ? score.toFixed(1) + '/100' : 'pending'}.`);
      } catch (saveErr) {
        console.error('Failed to auto-save candidate to HR', saveErr);
      }
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

  const handleStepChange = (newStep: EvaluationStep) => {
    setStep(newStep);
    if (typeof window !== 'undefined') {
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const currentScrollY = window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0;
      if (currentScrollY > 80) {
        window.scrollTo({
          top: 0,
          behavior: prefersReducedMotion ? 'auto' : 'smooth',
        });
      }
    }
  };

  function newEvaluation() {
    if (typeof window !== 'undefined') {
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({
        top: 0,
        behavior: prefersReducedMotion ? 'auto' : 'smooth',
      });
    }
    setIntake(null);
    setSources([]);
    setIdentity('');
    setFileName('');
    setFileSize(0);
    setRole('backend');
    setJd('');
    setJdFileName('');
    setJdFileSize(0);
    setJdLoading(false);
    setJdError('');
    setJdWarning('');
    setError('');
    setSourceError('');
    setPreviousRunNotice('');
    setHrSavedNotice('');
    setStep(0);
    setShowWizard(true);
  }

  return (
    <div className={`${styles.app} observatory-route observatory-route--live`}>
      <PlatformHeader surface="live" status="live" />
      <main className={styles.appBody}>
        <AnimatePresence mode="wait">
          {showWizard && (
            <motion.div
              key="wizard"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            >
              <AnalysisWizard
                step={step}
                intake={intake}
                fileName={fileName}
                fileSize={fileSize}
                role={role}
                jd={jd}
                jdFileName={jdFileName}
                jdFileSize={jdFileSize}
                jdLoading={jdLoading}
                jdError={jdError}
                jdWarning={jdWarning}
                sources={sources}
                identity={identity}
                busy={isBusy}
                phase={phase}
                error={error}
                sourceError={sourceError}
                previousRun={result}
                onStepChange={handleStepChange}
                onUpload={upload}
                onRemoveResume={removeResume}
                onRoleChange={setRole}
                onJdChange={setJd}
                onJdUpload={uploadJd}
                onJdRemove={removeJd}
                onToggleSource={toggleSource}
                onAddSource={addSource}
                onIdentityChange={setIdentity}
                onAnalyze={analyze}
                onFetchLink={fetchLink}
                onFetchAllCloud={fetchAllCloud}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {previousRunNotice && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className={styles.previousRunNotice}
              role="status"
              aria-live="polite"
            >
              {previousRunNotice}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {hrSavedNotice && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              style={{
                margin: '0.75rem auto 1.25rem',
                maxWidth: '1200px',
                padding: '0.75rem 1.25rem',
                borderRadius: '12px',
                background: 'rgba(99, 102, 241, 0.12)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                color: '#c7d2fe',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '1rem',
                fontSize: '0.875rem',
                flexWrap: 'wrap'
              }}
              role="status"
              aria-live="polite"
            >
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                <strong style={{ color: '#818cf8' }}>✓ Saved in HR:</strong> {hrSavedNotice}
              </span>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '1rem' }}>
                <Link href="/hr" scroll={true} style={{ color: '#818cf8', fontWeight: 600, textDecoration: 'underline', whiteSpace: 'nowrap' }}>
                  Candidates →
                </Link>
                <Link href="/" scroll={true} style={{ color: '#a5b4fc', fontWeight: 600, textDecoration: 'underline', whiteSpace: 'nowrap' }}>
                  Home →
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {result && (
            <motion.div
              key={result.dossier.analysis_run_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            >
              <LiveDossier result={result} onNewEvaluation={newEvaluation} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className={styles.appFooter}>
        <span>CandidateX · Research-informed technical decision support. Candidate profiles & scores are automatically saved to the Candidates (HR) tab at the end of each review.</span>
        <span>Resume identity and account association are declarations; static observations do not verify mastery or job performance.</span>
      </footer>
    </div>
  );
}