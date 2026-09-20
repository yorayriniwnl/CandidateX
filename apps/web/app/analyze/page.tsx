'use client';

import Link from 'next/link';
import { useRef, useState } from 'react';
import type { CanonicalRole, CapabilityKey } from '../../types/cci';
import { liveRequest, publicUrl, type LiveResult, type ResumeIntake } from '../../lib/live-analysis';
import { label } from '../../lib/research-demo';
import styles from './shared.module.css';
import live from './page.module.css';

const ROLES: CanonicalRole[] = ['backend', 'frontend', 'fullstack', 'ml_engineer', 'devops_cloud', 'data_engineer'];

export default function LiveAnalysisPage() {
  const [intake, setIntake] = useState<ResumeIntake | null>(null);
  const [result, setResult] = useState<LiveResult | null>(null);
  const [role, setRole] = useState<CanonicalRole>('backend');
  const [jd, setJd] = useState('');
  const [links, setLinks] = useState('');
  const [identity, setIdentity] = useState('');
  const [error, setError] = useState('');
  const [phase, setPhase] = useState<'idle' | 'upload' | 'analyze'>('idle');
  const [capability, setCapability] = useState<CapabilityKey>('backend_engineering');
  const busy = useRef(false);
  const isBusy = phase !== 'idle';

  async function upload(file?: File) {
    if (!file || busy.current) return;
    setError(''); setResult(null); setIntake(null); setLinks(''); setIdentity('');
    if (!/\.(pdf|docx)$/i.test(file.name)) { setError('Choose a PDF or DOCX resume.'); return; }
    if (file.size > 3 * 1024 * 1024) { setError('Resume must be 3 MB or smaller.'); return; }
    busy.current = true; setPhase('upload');
    try {
      const parsed = await liveRequest<ResumeIntake>('intake', file, file.name);
      setIntake(parsed);
      setLinks(parsed.manifest.github_urls.slice(0, 6).join('\n'));
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
        github_urls: links.split(/\r?\n/).map(s => s.trim()).filter(Boolean), github_identity: identity.trim() }));
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

  return <main className={styles.page}>
    <nav className={styles.nav}><Link href="/" className={styles.brand}>CandidateX</Link><div className={live.navLinks}><span className={styles.eyebrow}>Live evidence analysis</span><Link href="/research-demo">Research demonstration</Link></div></nav>
    <header className={styles.hero}><div className={styles.eyebrow}>Resume → Public evidence → Technical interview</div><h1>A resume is the beginning.<br />Follow the evidence.</h1><p>Upload a real resume. Review its extracted links, fetch public GitHub projects live, and inspect the technical evidence behind a role-aware assessment.</p></header>
    <div className={styles.layout}>
      <aside className={`${styles.panel} ${styles.controls}`}>
        <div className={styles.eyebrow}>01 / Candidate & role</div><h2>Start with the resume</h2>
        <label htmlFor="resume-upload" className={live.upload}>Upload resume · PDF or DOCX<input id="resume-upload" type="file" accept=".pdf,.docx" disabled={isBusy} onChange={e => void upload(e.target.files?.[0])} /></label>
        <p className={styles.muted}>Up to 3 MB. Digital PDFs only; scanned images need OCR. The document is processed for this request and is not saved.</p>
        <label htmlFor="live-role">Target role</label><select id="live-role" disabled={isBusy} value={role} onChange={e => { setRole(e.target.value as CanonicalRole); setResult(null); }}>{ROLES.map(r => <option key={r} value={r}>{label(r)}</option>)}</select>
        <label htmlFor="live-jd">Job description (optional)</label><textarea id="live-jd" maxLength={20000} disabled={isBusy} placeholder="Paste the role requirements…" value={jd} onChange={e => { setJd(e.target.value); setResult(null); }} />
        {intake && <>
          <label htmlFor="github-links">GitHub links to fetch</label><textarea id="github-links" disabled={isBusy} value={links} onChange={e => { setLinks(e.target.value); setResult(null); }} placeholder="https://github.com/username/repository" />
          <p className={styles.muted}>One profile or repository URL per line, up to 6 links. Profile links expand to recent public repositories; up to 3 repositories are inspected.</p>
          <label htmlFor="github-identity">Candidate’s GitHub username</label><input id="github-identity" type="text" maxLength={39} disabled={isBusy} value={identity} onChange={e => { setIdentity(e.target.value); setResult(null); }} placeholder="Username stated by the candidate" />
          <p className={styles.muted}>Used to match recent commit authors. Leave blank if unknown. A repository link alone does not prove authorship; unknown ownership leaves capability unscored.</p>
          <button className={`${styles.button} ${styles.primary}`} onClick={() => void analyze()} disabled={isBusy}>Fetch live evidence & analyze</button>
        </>}
      </aside>

      <div className={styles.stack}>
        {error && <div role="alert" className={styles.error}>{error}</div>}
        {isBusy && <div role="status" className={styles.notice}>{phase === 'upload' ? 'Reading the uploaded document and extracting text and links…' : 'Fetching public GitHub metadata and commit snapshots, inspecting files, and calculating the dossier. This can take up to a minute…'}</div>}
        {!intake && !isBusy && <section className={`${styles.panel} ${styles.empty}`}><div className={styles.eyebrow}>Your candidate. Their actual work.</div><h2>Evidence starts with an upload.</h2><p>The result uses files retrieved from the supplied public GitHub links. Resume claims stay separate from observed technical evidence.</p><div className={styles.steps}><span>1. Upload</span><span>2. Review links</span><span>3. Fetch live</span><span>4. Inspect & export</span></div><p className={styles.muted}>Private repositories, LinkedIn, coding profiles, credentials, and external portfolio/deployment sites are not automatically verified. Extracted links remain visible with their status.</p></section>}
        {intake && <section className={styles.panel}>
          <div className={styles.eyebrow}>02 / Extracted resume · Review before fetching</div><h2>{intake.manifest.display_name}</h2><p className={styles.muted}>{intake.filename}{intake.manifest.email ? ` · ${intake.manifest.email}` : ''}</p>
          <div className={styles.factors}>{intake.manifest.claimed_skills.map((s, i) => <span key={`${i}-${s}`}>{s}</span>)}</div>
          <p className={styles.muted}>Skills above are self-reported. Scores below require observed repository evidence.</p>
          <details className={styles.evidence}><summary>Inspect extracted text and document hash</summary><pre className={live.extracted}>{intake.text_preview}</pre><p className={styles.hash}>SHA-256: {intake.document_sha256}</p></details>
          {otherLinks.length > 0 && <details className={styles.evidence}><summary>Other extracted links ({otherLinks.length}) · not fetched</summary>{otherLinks.map((url, i) => <p className={live.sourceUrl} key={`${i}-${url}`}><a href={publicUrl(url)} target="_blank" rel="noreferrer">{url}</a></p>)}</details>}
          {intake.warnings.map(w => <p key={w} className={styles.warning}>{w}</p>)}
        </section>}
        {result && <>
          <section className={styles.panel} aria-label="Live assessment result">
            <div className={styles.resultHead}><div><div className={styles.eyebrow}>03 / Live assessment · {result.dossier.role}</div><h2>Technical evidence dossier</h2><p className={styles.muted}>{result.status === 'partial' ? 'Partial evidence — review source statuses below.' : 'Live acquisition completed.'} No synthetic observations.</p></div><button className={styles.button} onClick={exportResult}>Export dossier JSON</button></div>
            <div className={styles.metrics}><div className={styles.metric}><span>Role Capability Index</span><strong>{result.dossier.rci?.toFixed(1) ?? 'Unknown'}</strong><span>Observed capability / 100</span></div><div className={styles.metric}><span>Evidence coverage</span><strong>{(result.dossier.coverage * 100).toFixed(1)}%</strong><span>Separate from capability</span></div><div className={styles.metric}><span>Static observations</span><strong>{result.dossier.evidence_records.length}</strong><span>From retrieved artifacts</span></div></div>
            {result.dossier.is_insufficient_evidence && <p className={styles.warning}>Insufficient evidence for a broad assessment. Unknown capabilities are not zero. Use the interview probes to resolve gaps.</p>}
            {!identity.trim() && <p className={styles.warning}>No GitHub username was declared. Repository observations are retained, but ownership confidence is zero and they do not establish this candidate’s capability.</p>}
            <p className={styles.muted}>This supports a technical interview; it does not make hiring decisions or establish job-performance accuracy.</p>
          </section>
          <section className={styles.panel}><div className={styles.eyebrow}>04 / Acquisition receipts</div><h2>What was fetched</h2>{result.sources.length === 0 && <p className={styles.warning}>No public sources were selected. Resume declarations alone are not scored.</p>}{result.sources.map((s, i) => <article className={styles.evidence} key={`${i}-${s.url}`}><div className={live.sourceHead}><a className={live.sourceUrl} href={publicUrl(s.url)} target="_blank" rel="noreferrer">{s.url}</a><span className={styles.tag}>{label(s.status)}</span></div><p className={styles.muted}>{s.detail}</p>{s.commit_sha && <><p className={styles.hash}>Commit {s.commit_sha}</p><p className={styles.muted}>{s.files_inspected} files inspected · {s.files_omitted} omitted · {s.evidence_count} observations · fetched {s.fetched_at}</p></>}{s.expanded_repositories?.map(url => <p className={styles.hash} key={url}>{url}</p>)}</article>)}</section>
          <section className={styles.panel}><div className={styles.eyebrow}>05 / Capability & observability</div><h2>Twelve capabilities, traceable evidence</h2><div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>Capability</th><th>Estimate</th><th>Coverage</th><th>95% interval</th><th>Observations</th></tr></thead><tbody>{Object.values(result.dossier.capability_estimates).map(cap => <tr key={cap.capability_key}><td><button onClick={() => setCapability(cap.capability_key)}>{label(cap.capability_key)}</button></td><td>{cap.estimate?.toFixed(1) ?? 'Unknown'}</td><td>{(cap.coverage_k * 100).toFixed(1)}%</td><td>{cap.ci_lower == null ? 'Unavailable' : `${cap.ci_lower.toFixed(1)}–${cap.ci_upper?.toFixed(1)}`}</td><td>{cap.raw_evidence_count}</td></tr>)}</tbody></table></div><p className={styles.muted}>Confidence intervals require at least two independent project clusters. Single-repository results cannot provide that interval.</p></section>
          <section className={styles.panel}><div className={styles.eyebrow}>06 / Inspect the source</div><h2>{label(capability)}</h2><p className={styles.muted}>Select a capability above to inspect its observations. GitHub links open the exact fetched commit.</p>{evidence.length === 0 && <p className={styles.warning}>No observations for this capability.</p>}{evidence.map(e => <details className={styles.evidence} key={e.evidence_id}><summary>{e.provenance.artifact_path || 'Repository structure'} · support {e.support_score.toFixed(0)} · confidence {(e.confidence * 100).toFixed(1)}%</summary><dl><dt>Artifact</dt><dd><a href={publicUrl(e.provenance.artifact_url)} target="_blank" rel="noreferrer">{e.provenance.artifact_path || e.source_locator}</a></dd><dt>Commit</dt><dd>{e.immutable_revision}</dd><dt>Location</dt><dd>{e.provenance.symbol_or_line || 'File-level inspection'}</dd><dt>Fingerprint</dt><dd>{e.fingerprint}</dd><dt>Artifact SHA-256</dt><dd>{e.provenance.artifact_sha256}</dd><dt>Observation</dt><dd><pre className={live.extracted}>{e.provenance.raw_support_text}</pre></dd></dl><div className={styles.factors}>{Object.entries(e.confidence_factors).map(([key, value]) => <span key={key}>{label(key)}: {value.toFixed(3)}</span>)}</div></details>)}</section>
          <section className={styles.panel}><div className={styles.eyebrow}>07 / Prepare the interview</div><h2>Questions grounded in evidence and gaps</h2>{result.dossier.interview_questions.map(q => <article className={styles.question} key={q.question_id}><h3>{label(q.target_capability)}</h3><p>{q.question_text}</p><p className={styles.muted}>{q.rationale}</p><p className={styles.muted}>{q.verification_guidance}</p><button className={styles.button} onClick={() => setCapability(q.target_capability)}>Inspect related evidence</button></article>)}</section>
          <section className={styles.panel}><h2>Assessment limits</h2>{result.dossier.system_limitations.map((text, i) => <p className={styles.muted} key={i}>{text}</p>)}</section>
        </>}
      </div>
    </div>
    <footer className={styles.footer}>CandidateX · Research-informed technical decision support. Export the dossier to keep it; this page does not retain resumes or results across refreshes.</footer>
  </main>;
}
