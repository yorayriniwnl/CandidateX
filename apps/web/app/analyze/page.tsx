'use client';

import { useRef, useState } from 'react';
import { ArrowUpRight, FileText, ShieldCheck, Sparkles } from 'lucide-react';
import type { AnalysisConfidenceSummary, CanonicalRole, CapabilityKey } from '../../types/cci';
import { getAnalysisConfidence, getSourceHealth, liveRequest, publicUrl, type LiveResult, type ResumeIntake, type SourceHealth } from '../../lib/live-analysis';
import { label } from '../../lib/evidence';
import { PlatformHeader } from '../../components/navigation/PlatformHeader';
import styles from './shared.module.css';
import live from './page.module.css';
import { DetailedAnalysis, ResumeSections, SourceDetails } from './DetailedAnalysis';
import { EvidenceStrengthPanel } from './ConfidencePanel';

const ROLES: CanonicalRole[] = ['backend', 'frontend', 'fullstack', 'ml_engineer', 'devops_cloud', 'data_engineer'];

function CapabilitySnapshotTable({
  estimates,
  confidence,
  sourceHealth,
  selectedCapability,
  onSelectCapability,
}: {
  estimates: LiveResult['dossier']['capability_estimates'];
  confidence: AnalysisConfidenceSummary;
  sourceHealth: SourceHealth;
  selectedCapability: CapabilityKey;
  onSelectCapability: (key: CapabilityKey) => void;
}) {
  const capabilities = Object.values(estimates);

  return <>
    <div className={styles.tableIntro}>
      <div>
        <h3>Evidence at a glance</h3>
        <p className={styles.muted}>Select a capability to inspect the exact source evidence behind it.</p>
      </div>
      <span className={styles.tableHint}>12 capability areas</span>
    </div>
    <div className={styles.tableWrap}>
      <table className={`${styles.table} ${styles.capabilityTable}`} aria-label="Capability snapshot">
        <thead>
          <tr>
            <th scope="col">Capability</th>
            <th scope="col">Observed score</th>
            <th scope="col">Status</th>
            <th scope="col">Coverage</th>
            <th scope="col">Next step</th>
          </tr>
        </thead>
        <tbody>
          {capabilities.map(cap => {
            const isObserved = cap.is_observed && cap.estimate !== null;
            const hasInterval = cap.ci_lower != null && cap.ci_upper != null;
            const globalUncertainty = confidence.evidence_strength !== 'well_supported'
              || sourceHealth.failed_sources > 0
              || sourceHealth.not_selected_sources > 0
              || sourceHealth.not_scanned_sources > 0;
            const isConservative = isObserved && (globalUncertainty || cap.coverage_k < 0.35 || !hasInterval);
            const score = cap.estimate ?? 0;
            const coverage = Math.round(cap.coverage_k * 100);
            return <tr key={cap.capability_key} className={selectedCapability === cap.capability_key ? styles.selectedRow : undefined}>
              <td data-label="Capability">
                <button
                  type="button"
                  className={styles.capabilityButton}
                  aria-pressed={selectedCapability === cap.capability_key}
                  onClick={() => onSelectCapability(cap.capability_key)}
                >
                  <span className={styles.capabilityTitle}>{label(cap.capability_key)}</span>
                  <span className={styles.capabilitySubtext}>{isObserved ? `${cap.raw_evidence_count} observed ${cap.raw_evidence_count === 1 ? 'signal' : 'signals'}` : 'No independent evidence yet'}</span>
                </button>
              </td>
              <td data-label="Observed score">
                <div className={styles.readinessCell}>
                  <div className={styles.readinessValue}>{isObserved ? `${cap.estimate?.toFixed(1)} / 100` : 'Unknown'}</div>
                  <div className={styles.readinessBar} aria-hidden="true"><span style={{ width: `${isObserved ? Math.min(100, score) : 0}%` }} /></div>
                </div>
              </td>
              <td data-label="Status"><span className={`${styles.statusPill} ${isObserved && !isConservative ? styles.statusGood : styles.statusNeedsReview}`}>{isConservative ? 'Limited evidence' : isObserved ? 'Evidence found' : 'Needs verification'}</span></td>
              <td data-label="Coverage"><div className={styles.coverageCell}><strong>{coverage}%</strong><span>role signal</span></div></td>
              <td data-label="Next step"><button type="button" className={styles.rowAction} onClick={() => onSelectCapability(cap.capability_key)}>{isConservative ? 'Prepare verification' : isObserved ? 'View evidence' : 'Prepare question'} <span aria-hidden="true">→</span></button></td>
            </tr>;
          })}
        </tbody>
      </table>
    </div>
    <details className={styles.auditDetails}>
      <summary>Show audit details <span>Confidence intervals and observation counts</span></summary>
      <div className={styles.tableWrap}>
        <table className={styles.table} aria-label="Capability audit details">
          <thead>
            <tr>
              <th scope="col">Capability</th>
              <th scope="col">95% interval</th>
              <th scope="col">Observations</th>
              <th scope="col">Effective count</th>
              <th scope="col">Coverage</th>
            </tr>
          </thead>
          <tbody>
            {capabilities.map(cap => <tr key={cap.capability_key}>
              <td data-label="Capability">{label(cap.capability_key)}</td>
              <td data-label="95% interval">{cap.ci_lower == null ? 'Unavailable' : `${cap.ci_lower.toFixed(1)}–${cap.ci_upper?.toFixed(1)}`}</td>
              <td data-label="Observations">{cap.raw_evidence_count}</td>
              <td data-label="Effective count">{cap.effective_evidence_count.toFixed(1)}</td>
              <td data-label="Coverage">{(cap.coverage_k * 100).toFixed(1)}%</td>
            </tr>)}
          </tbody>
        </table>
      </div>
      <p className={styles.muted}>Confidence intervals require at least two independent project clusters. Single-repository results cannot provide that interval.</p>
    </details>
  </>;
}

export default function LiveAnalysisPage() {
  const [intake, setIntake] = useState<ResumeIntake | null>(null);
  const [result, setResult] = useState<LiveResult | null>(null);
  const [role, setRole] = useState<CanonicalRole>('backend');
  const [jd, setJd] = useState('');
  const [links, setLinks] = useState('');
  const [identity, setIdentity] = useState('');
  const [externalLinks, setExternalLinks] = useState('');
  const [error, setError] = useState('');
  const [phase, setPhase] = useState<'idle' | 'upload' | 'analyze'>('idle');
  const [capability, setCapability] = useState<CapabilityKey>('backend_engineering');
  const busy = useRef(false);
  const isBusy = phase !== 'idle';

  async function upload(file?: File) {
    if (!file || busy.current) return;
    setError(''); setResult(null); setIntake(null); setLinks(''); setIdentity(''); setExternalLinks('');
    if (!/\.(pdf|docx)$/i.test(file.name)) { setError('Choose a PDF or DOCX resume.'); return; }
    if (file.size > 3 * 1024 * 1024) { setError('Resume must be 3 MB or smaller.'); return; }
    busy.current = true; setPhase('upload');
    try {
      const parsed = await liveRequest<ResumeIntake>('intake', file, file.name);
      setIntake(parsed);
      setLinks(parsed.manifest.github_urls.slice(0, 20).join('\n'));
      setExternalLinks([...new Set(['linkedin_urls', 'coding_profile_urls', 'credential_urls', 'deployment_urls', 'portfolio_urls', 'project_links'].flatMap(key => parsed.manifest[key as keyof ResumeIntake['manifest']] as string[]))].slice(0, 100).join('\n'));
      const profile = parsed.manifest.github_urls.find(url => { try { return new URL(url).pathname.split('/').filter(Boolean).length === 1; } catch { return false; } });
      setIdentity(profile ? new URL(profile).pathname.replaceAll('/', '') : '');
    } catch (e) { setError(e instanceof Error ? e.message : 'Resume could not be parsed.'); }
    finally { busy.current = false; setPhase('idle'); }
  }

  async function analyze() {
    if (!intake || busy.current) return;
    busy.current = true; setPhase('analyze'); setError(''); setResult(null);
    try {
      const data = await liveRequest<LiveResult>('analyze', JSON.stringify({ intake, role, jd_text: jd,
        github_urls: links.split(/\r?\n/).map(s => s.trim()).filter(Boolean), github_identity: identity.trim(),
        external_urls: externalLinks.split(/\r?\n/).map(s => s.trim()).filter(Boolean) }));
      setResult(data);
      const observed = Object.values(data.dossier.capability_estimates).find(c => c.is_observed);
      if (observed) setCapability(observed.capability_key);
    } catch (e) { setError(e instanceof Error ? e.message : 'Analysis could not complete.'); }
    finally { busy.current = false; setPhase('idle'); }
  }

  function exportResult() {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a'); anchor.href = url;
    anchor.download = `candidatex-${result.dossier.analysis_run_id}.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const evidence = result?.dossier.evidence_records.filter(e => e.target_capability === capability) ?? [];
  const otherLinks = intake ? ['linkedin_urls', 'coding_profile_urls', 'credential_urls', 'deployment_urls', 'portfolio_urls', 'project_links'].flatMap(key => intake.manifest[key as keyof ResumeIntake['manifest']] as string[]) : [];
  const currentStep = result ? 3 : intake ? 2 : 1;

  return <div className={`${styles.shell} observatory-route observatory-route--live`}>
    <PlatformHeader surface="live" status="live" />
    <main className={styles.page}>
    <header className={styles.hero}>
      <div className={styles.eyebrow}><span className={styles.eyebrowDot} aria-hidden="true" />Live evidence workspace <span className={styles.eyebrowDivider}>/</span> request scoped</div>
      <div className={styles.heroLayout}>
        <div className={styles.heroMain}>
          <h1>Turn a resume into <span className={styles.heroAccent}>better questions.</span></h1>
          <p>Upload once. CandidateX separates claims from observed evidence, shows what is still unknown, and gives a human interviewer a sharper next move.</p>
          <div className={styles.heroSignals} aria-label="CandidateX review principles">
            <span><Sparkles size={13} aria-hidden="true" /> Evidence-first</span>
            <span><ShieldCheck size={13} aria-hidden="true" /> Human-led</span>
            <span><FileText size={13} aria-hidden="true" /> Request-only</span>
          </div>
        </div>
        <div className={styles.heroCallout}>
          <div className={styles.calloutTop}><span className={styles.calloutIndex}>01</span><span className={styles.eyebrow}>The CandidateX loop</span></div>
          <p>Claims, evidence, and unknowns stay separate. The result supports an interview; it never makes the hiring decision.</p>
          <div className={styles.calloutFlow} aria-label="Claims to evidence to interview"><span>Claims</span><i aria-hidden="true">→</i><span>Evidence</span><i aria-hidden="true">→</i><span>Interview</span></div>
        </div>
      </div>
    </header>
    <div className={styles.layout}>
      <aside className={`${styles.panel} ${styles.controls}`}>
        <div className={styles.workflowHeader}><div><div className={styles.eyebrow}>Candidate review</div><h2>Build the review</h2></div><span className={styles.stepCount}>0{currentStep}<small>/03</small></span></div>
        <label htmlFor="resume-upload" className={`${live.upload} ${styles.uploadCard}`}>
          <span className={live.uploadMark} aria-hidden="true"><FileText size={20} /></span>
          <span className={live.uploadCopy}><strong>Drop your resume here</strong><small>PDF or DOCX · up to 3 MB</small></span>
          <span className={live.uploadAction}>Browse files <ArrowUpRight size={14} aria-hidden="true" /></span>
          <input id="resume-upload" aria-label="Upload resume" type="file" accept=".pdf,.docx" disabled={isBusy} onChange={e => void upload(e.currentTarget.files?.[0])} />
        </label>
        <p className={styles.privacyNote}><ShieldCheck size={14} aria-hidden="true" /> Processed for this request · never saved</p>
        <ol className={styles.progress} aria-label="Review progress">
          <li className={currentStep >= 1 ? styles.progressActive : undefined}><span>1</span><div><strong>Upload resume</strong><small>PDF or DOCX, up to 3 MB</small></div></li>
          <li className={currentStep >= 2 ? styles.progressActive : undefined}><span>2</span><div><strong>Review sources</strong><small>Confirm public links</small></div></li>
          <li className={currentStep >= 3 ? styles.progressActive : undefined}><span>3</span><div><strong>Inspect evidence</strong><small>Find gaps and prepare</small></div></li>
        </ol>
        <div className={styles.contextHeading}><span>Shape the review</span><small>Optional context</small></div>
        <div className={styles.fieldGroup}><label htmlFor="live-role">Target role</label><select id="live-role" disabled={isBusy} value={role} onChange={e => { setRole(e.target.value as CanonicalRole); setResult(null); }}>{ROLES.map(r => <option key={r} value={r}>{label(r)}</option>)}</select></div>
        <div className={styles.fieldGroup}><label htmlFor="live-jd">Job description <span>optional</span></label><textarea id="live-jd" maxLength={20000} disabled={isBusy} placeholder="Paste the role requirements…" value={jd} onChange={e => { setJd(e.target.value); setResult(null); }} /></div>
        {intake && <>
          <details className={styles.advanced}>
            <summary>Review public sources (optional)<span>GitHub, portfolio, certificates</span></summary>
            <div className={styles.advancedBody}>
              <div className={styles.fieldGroup}><label htmlFor="github-links">GitHub links to fetch</label><textarea id="github-links" disabled={isBusy} value={links} onChange={e => { setLinks(e.target.value); setResult(null); }} placeholder="https://github.com/username/repository" /></div>
              <p className={styles.muted}>Up to 20 profile or repository URLs. Profiles include public repository inventory; selected repositories receive a deeper inspection.</p>
              <div className={styles.fieldGroup}><label htmlFor="github-identity">Candidate’s GitHub username</label><input id="github-identity" type="text" maxLength={39} disabled={isBusy} value={identity} onChange={e => { setIdentity(e.target.value); setResult(null); }} placeholder="Username stated by the candidate" /></div>
              <p className={styles.muted}>This helps match recent commit authors. Leave blank if the candidate did not state one.</p>
              <div className={styles.fieldGroup}><label htmlFor="external-links">Public portfolio, certificate and other links</label><textarea id="external-links" disabled={isBusy} value={externalLinks} onChange={e => { setExternalLinks(e.target.value); setResult(null); }} placeholder="https://issuer.example/verify/credential" /></div>
              <p className={styles.muted}>One URL per line. Login gates and unavailable pages remain visible as verification gaps.</p>
            </div>
          </details>
          <button aria-label="Fetch live evidence & analyze" className={`${styles.button} ${styles.primary}`} onClick={() => void analyze()} disabled={isBusy}>{isBusy ? 'Reviewing evidence…' : 'Run evidence review'}</button>
        </>}
      </aside>

      <div className={styles.stack}>
        {error && <div role="alert" className={styles.error}>{error}</div>}
        {isBusy && <div role="status" className={styles.notice}>{phase === 'upload' ? 'Reading résumé sections, skills and embedded links…' : 'Fetching GitHub profiles, repository snapshots and public pages. Matching skills and reviewing certificates, projects and experience. This can take up to a minute…'}</div>}
        {!intake && !isBusy && <section className={`${styles.panel} ${styles.empty}`}>
          <div className={styles.emptyTopline}><span className={styles.emptyReady}><span aria-hidden="true" />Ready when you are</span><span className={styles.emptyScope}>REQUEST-SCOPED</span></div>
          <div className={styles.emptyIcon} aria-hidden="true">01</div>
          <div className={styles.eyebrow}>Start with one resume</div>
          <h2>Upload a resume to begin</h2>
          <p className={styles.emptyLead}>We’ll extract the candidate’s claims first. You’ll review the public sources before anything is fetched.</p>
          <div className={styles.previewCard}>
            <div className={styles.previewHeader}><span>Your review will include</span><span>CandidateX / Live</span></div>
            <div className={styles.previewGrid}><div><strong>Claims</strong><small>Structured from the resume</small></div><div><strong>Receipts</strong><small>Public evidence, linked</small></div><div><strong>Questions</strong><small>Gaps made interviewable</small></div></div>
          </div>
          <div className={styles.stepsTitle}>Your review, in three moves</div>
          <div className={styles.steps}><span><b>1</b> Upload</span><span><b>2</b> Review</span><span><b>3</b> Analyze</span></div>
          <p className={styles.muted}>Private sources, login-protected pages, issuer authentication, and employment verification remain outside automated verification.</p>
        </section>}
        {intake && <section className={styles.panel}>
          <div className={styles.eyebrow}>02 / Extracted resume · Review before fetching</div><h2>{intake.manifest.display_name}</h2><p className={styles.muted}>{intake.filename}{intake.manifest.email ? ` · ${intake.manifest.email}` : ''}</p>
          <div className={styles.factors}>{intake.manifest.claimed_skills.map((s, i) => <span key={`${i}-${s}`}>{s}</span>)}</div>
          <p className={styles.muted}>Skills above are self-reported. Scores below require observed repository evidence.</p>
          <details className={styles.evidence}><summary>Inspect extracted text and document hash</summary><pre className={live.extracted}>{intake.text_preview}</pre><p className={styles.hash}>SHA-256: {intake.document_sha256}</p></details>
          <ResumeSections intake={intake} />
          {otherLinks.length > 0 && <details className={styles.evidence}><summary>Other extracted links ({otherLinks.length}) · review the fetch selection</summary>{otherLinks.map((url, i) => <p className={live.sourceUrl} key={`${i}-${url}`}><a href={publicUrl(url)} target="_blank" rel="noreferrer">{url}</a></p>)}</details>}
          {intake.warnings.map(w => <p key={w} className={styles.warning}>{w}</p>)}
        </section>}
        {result && <>
          <section id="review-summary" className={styles.panel} aria-label="Live assessment result">
            <div className={styles.resultHead}><div><div className={styles.eyebrow}>03 / Live assessment · {result.dossier.role}</div><div className={styles.resultTitle}><h2>Technical evidence dossier</h2><span className={`${styles.statusPill} ${result.status === 'partial' ? styles.statusNeedsReview : styles.statusGood}`}>{result.status === 'partial' ? 'Partial review' : 'Review complete'}</span></div><p className={styles.muted}>{result.status === 'partial' ? 'Some sources need attention below.' : 'Live acquisition completed.'} No synthetic observations.</p></div><button className={styles.button} onClick={exportResult}>Export dossier JSON</button></div>
            <div className={styles.metrics}><div className={styles.metric}><span>Observed capability index</span><strong>{result.dossier.rci?.toFixed(1) ?? 'Unknown'}</strong><span>Point estimate / 100, not a probability</span></div><div className={styles.metric}><span>Evidence coverage</span><strong>{(result.dossier.coverage * 100).toFixed(1)}%</strong><span>Separate from capability</span></div><div className={styles.metric}><span>Static observations</span><strong>{result.dossier.evidence_records.length}</strong><span>From retrieved artifacts</span></div></div>
            {result.dossier.is_insufficient_evidence && <p className={styles.warning}>Insufficient evidence for a broad assessment. Unknown capabilities are not zero. Use the interview probes to resolve gaps.</p>}
            {!identity.trim() && <p className={styles.warning}>No GitHub username was declared. Repository observations are retained, but ownership confidence is zero and they do not establish this candidate’s capability.</p>}
            <p className={styles.muted}>This supports a technical interview; it does not make hiring decisions or establish job-performance accuracy.</p>
          </section>
          <EvidenceStrengthPanel result={result} />
          {result.analysis && <DetailedAnalysis analysis={result.analysis} />}
          <nav className={styles.resultNav} aria-label="Review sections"><span>Jump to</span><a href="#acquisition-receipts">Receipts</a><a href="#capability-snapshot">Capabilities</a><a href="#evidence-inspector">Evidence</a><a href="#interview-questions">Interview</a></nav>
          <section id="acquisition-receipts" className={styles.panel}><div className={styles.eyebrow}>04 / Acquisition receipts</div><h2>What was fetched</h2>{result.sources.length === 0 && <p className={styles.warning}>No public sources were selected. Resume declarations alone are not scored.</p>}{result.sources.map((s, i) => <article className={styles.evidence} key={`${i}-${s.url}`}><div className={live.sourceHead}><a className={live.sourceUrl} href={publicUrl(s.url)} target="_blank" rel="noreferrer">{s.url}</a><span className={styles.tag}>{label(s.status)}</span></div><p className={styles.muted}>{s.detail}</p>{s.commit_sha && <><p className={styles.hash}>Commit {s.commit_sha}</p><p className={styles.muted}>{s.files_inspected} files inspected · {s.files_omitted} omitted · {s.evidence_count} observations · fetched {s.fetched_at}</p></>}<SourceDetails source={s} /></article>)}</section>
          <section id="capability-snapshot" className={`${styles.panel} ${styles.capabilityPanel}`}><div className={styles.eyebrow}>05 / Capability snapshot</div><h2>What the evidence shows</h2><p className={styles.muted}>Use the next step in each row to move from a score to a useful interview conversation.</p><CapabilitySnapshotTable estimates={result.dossier.capability_estimates} confidence={getAnalysisConfidence(result.dossier, result.analysis, getSourceHealth(result))} sourceHealth={getSourceHealth(result)} selectedCapability={capability} onSelectCapability={setCapability} /></section>
          <section id="evidence-inspector" className={styles.panel}><div className={styles.eyebrow}>06 / Inspect the source</div><h2>{label(capability)}</h2><p className={styles.muted}>Select a capability above to inspect its observations. GitHub links open the exact fetched commit.</p>{evidence.length === 0 && <p className={styles.warning}>No observations for this capability.</p>}{evidence.map(e => <details className={styles.evidence} key={e.evidence_id}><summary>{e.provenance.artifact_path || 'Repository structure'} · support {e.support_score.toFixed(0)} · confidence {(e.confidence * 100).toFixed(1)}%</summary><dl><dt>Artifact</dt><dd><a href={publicUrl(e.provenance.artifact_url)} target="_blank" rel="noreferrer">{e.provenance.artifact_path || e.source_locator}</a></dd><dt>Commit</dt><dd>{e.immutable_revision}</dd><dt>Location</dt><dd>{e.provenance.symbol_or_line || 'File-level inspection'}</dd><dt>Fingerprint</dt><dd>{e.fingerprint}</dd><dt>Artifact SHA-256</dt><dd>{e.provenance.artifact_sha256}</dd><dt>Observation</dt><dd><pre className={live.extracted}>{e.provenance.raw_support_text}</pre></dd></dl><div className={styles.factors}>{Object.entries(e.confidence_factors).map(([key, value]) => <span key={key}>{label(key)}: {value.toFixed(3)}</span>)}</div></details>)}</section>
          <section id="interview-questions" className={styles.panel}><div className={styles.eyebrow}>07 / Prepare the interview</div><h2>Questions grounded in evidence and gaps</h2>{result.dossier.interview_questions.map(q => <article className={styles.question} key={q.question_id}><h3>{label(q.target_capability)}</h3><p>{q.question_text}</p><p className={styles.muted}>{q.rationale}</p><p className={styles.muted}>{q.verification_guidance}</p><button className={styles.button} onClick={() => setCapability(q.target_capability)}>Inspect related evidence</button></article>)}</section>
          <section className={styles.panel}><h2>Assessment limits</h2>{result.dossier.system_limitations.map((text, i) => <p className={styles.muted} key={i}>{text}</p>)}</section>
        </>}
      </div>
    </div>
    <footer className={styles.footer}>CandidateX · Research-informed technical decision support. Export the dossier to keep it; this page does not retain resumes or results across refreshes.</footer>
    </main>
  </div>;
}
