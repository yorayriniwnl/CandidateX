'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import type { CapabilityKey, CanonicalRole } from '../../types/cci';
import { demoRequest, label, SOURCES, type DemoInput, type DemoResult, type Scenario } from '../../lib/research-demo';
import styles from './page.module.css';

const INITIAL: DemoInput = {
  candidate_id: 'd3333333-3333-4333-8333-333333333333', scenario: 'consistent', role: 'backend',
  jd_text: '', excluded_sources: [], ownership_multiplier: 1, reliability_false_positives: 0,
};
const ROLES: CanonicalRole[] = ['backend', 'frontend', 'fullstack', 'ml_engineer', 'devops_cloud', 'data_engineer'];
const SCENARIOS: { value: Scenario; name: string; description: string }[] = [
  { value: 'consistent', name: 'Consistent evidence', description: 'Seven simulated source families across three project clusters. A backend-oriented profile makes role differences visible.' },
  { value: 'sparse', name: 'Sparse evidence', description: 'One project with GitHub observations for backend, database and testing only. Other capabilities remain unknown; intervals are not estimable.' },
  { value: 'low_ownership', name: 'Ambiguous GitHub ownership', description: 'The same observations, with GitHub ownership confidence reduced to 5% of its original value.' },
  { value: 'conflicting', name: 'Conflicting observations', description: 'Three source families report negative backend and database observations. The contradictory evidence stays visible.' },
  { value: 'empty', name: 'No usable evidence', description: 'No observations. Capability is unknown, coverage is zero, and interview questions target missing evidence.' },
];
const number = (value: number | null, digits = 1) => value === null ? 'Unknown' : value.toFixed(digits);
const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

export default function ResearchDemonstration() {
  const [input, setInput] = useState<DemoInput>(INITIAL);
  const [result, setResult] = useState<DemoResult | null>(null);
  const [previous, setPrevious] = useState<DemoResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<CapabilityKey>('backend_engineering');
  const [overrideCap, setOverrideCap] = useState<CapabilityKey>('backend_engineering');
  const [justification, setJustification] = useState('');
  const inspector = useRef<HTMLElement>(null);
  const inFlight = useRef(false);
  const dirty = !!result && JSON.stringify(input) !== JSON.stringify(result.input);
  const dossier = result?.dossier;
  const conflictCount = dossier ? Object.values(dossier.capability_conflicts).filter(c => c.has_meaningful_conflict).length : 0;
  const selectedEvidence = dossier?.evidence_records.filter(e => e.target_capability === selected) || [];
  const sumConfidence = selectedEvidence.reduce((sum, e) => sum + e.confidence, 0);
  const sumWeightedSupport = selectedEvidence.reduce((sum, e) => sum + e.confidence * e.support_score, 0);
  const update = (changes: Partial<DemoInput>) => { setInput(current => ({ ...current, ...changes })); setError(''); };

  async function run() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true); setError(''); setPrevious(result); setResult(null);
    try {
      const next = await demoRequest<DemoResult>('run', input);
      if (next.dossier.candidate_id !== input.candidate_id || next.graph.analysis_run_id !== next.dossier.analysis_run_id) throw new Error('Result identity mismatch. No dossier displayed.');
      setResult(next);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The run failed. No result substituted.'); }
    finally { inFlight.current = false; setBusy(false); }
  }

  async function override() {
    if (!result || dirty || inFlight.current) return;
    inFlight.current = true; setBusy(true); setError('');
    try {
      const revised = await demoRequest<Pick<DemoResult, 'dossier' | 'graph' | 'graph_snapshot'>>('rescore', {
        run_id: result.dossier.analysis_run_id, weights: { [overrideCap]: 1 }, justification,
      });
      if (revised.dossier.candidate_id !== result.dossier.candidate_id) throw new Error('Result identity mismatch.');
      setPrevious(result); setResult({ ...result, ...revised });
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Override failed. The displayed snapshot is unchanged.'); }
    finally { inFlight.current = false; setBusy(false); }
  }

  function exportSnapshot() {
    if (!result || dirty) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a'); anchor.href = url;
    anchor.download = `candidatex-research-${result.dossier.dossier_id}.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function inspect(cap: CapabilityKey) { setSelected(cap); inspector.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }

  return <main className={styles.page}>
    <nav className={styles.nav} aria-label="Research navigation">
      <div><span className={styles.brand}>CandidateX</span> <span className={styles.eyebrow}> / Research demonstration</span></div>
      <div className="flex gap-5"><a href="#method">The method</a><a href="#benchmarks">Experiments</a><Link href="/workspace">Prototype workspace</Link></div>
    </nav>
    <header className={styles.hero}>
      <div className={styles.eyebrow}>Candidate Capability Intelligence · Interactive research prototype</div>
      <h1>From evidence to interview.</h1>
      <p>Explore how the same technical evidence changes meaning for a different role. Separate capability from coverage, inspect each observation, and turn uncertainty into a focused interview.</p>
    </header>
    <div className={styles.notice}><strong>Controlled synthetic demonstration.</strong> All candidate observations and source-review counts on this page are simulated. Calculations run through the CCI backend. No real person is assessed and no external repository is fetched.</div>
    <div className={styles.layout}>
      <aside className={`${styles.panel} ${styles.controls}`}>
        <div className={styles.eyebrow}>01 / Set the conditions</div><h2>One candidate. Different evidence.</h2>
        <p className={styles.muted}>Synthetic candidate A · fixed observations, independent of the target role.</p>
        <fieldset disabled={busy}>
          <label htmlFor="scenario">Evidence scenario</label>
          <select id="scenario" value={input.scenario} onChange={e => update({ scenario: e.target.value as Scenario })}>
            {SCENARIOS.map(s => <option key={s.value} value={s.value}>{s.name}</option>)}
          </select>
          <p className={`${styles.muted} mt-2`}>{SCENARIOS.find(s => s.value === input.scenario)?.description}</p>
          <label htmlFor="role">Target role</label>
          <select id="role" value={input.role} onChange={e => update({ role: e.target.value as CanonicalRole })}>{ROLES.map(role => <option key={role} value={role}>{label(role)}</option>)}</select>
          <label htmlFor="jd">Job description</label>
          <textarea id="jd" value={input.jd_text} onChange={e => update({ jd_text: e.target.value })} maxLength={20000} placeholder="Optional: Must have Python and PostgreSQL. Preferred: Docker and testing." />
          <p className={styles.muted}>Leave blank to use canonical role priors. Recognized JD terms adjust capability weights.</p>
          <label>Include source families</label>
          <div className={styles.sources}>{SOURCES.map(source => <label key={source}><input type="checkbox" checked={!input.excluded_sources.includes(source)} onChange={e => update({ excluded_sources: e.target.checked ? input.excluded_sources.filter(s => s !== source) : [...input.excluded_sources, source] })} />{source}</label>)}</div>
          <label htmlFor="ownership">Ownership multiplier: {percent(input.ownership_multiplier)}</label>
          <input id="ownership" type="range" min="0" max="1" step="0.05" value={input.ownership_multiplier} onChange={e => update({ ownership_multiplier: Number(e.target.value) })} />
          <label htmlFor="false-positive">Simulated false positives per source: {input.reliability_false_positives}</label>
          <input id="false-positive" type="range" min="0" max="100" step="1" value={input.reliability_false_positives} onChange={e => update({ reliability_false_positives: Number(e.target.value) })} />
          <p className={styles.muted}>Each source starts with eight simulated true positives and its configured Beta prior. These are demonstration assumptions.</p>
          <button className={`${styles.button} ${styles.primary}`} onClick={run}>{busy ? 'Computing from evidence…' : 'Run demonstration'}</button>
          <button className={`${styles.button} mt-3 w-full`} onClick={() => update(INITIAL)}>Reset inputs</button>
        </fieldset>
      </aside>
      <div className={styles.stack} aria-busy={busy}>
        {error && <div role="alert" className={styles.error}>{error}</div>}
        {dirty && <div role="status" className={styles.notice}>Inputs changed. Run again to update the results.</div>}
        {!result && <section className={`${styles.panel} ${styles.empty}`}>
          <div className={styles.eyebrow}>02 / Observe the mechanism</div>
          <h2>{busy ? 'Calculating the dossier…' : 'A score should have an explanation.'}</h2>
          <p>{busy ? 'The backend is applying confidence factors, clustering evidence, calculating role weights, and generating evidence-linked interview questions.' : 'Run a scenario to see the actual calculations. Then change one input at a time and compare the resulting capability, coverage, and interview priorities.'}</p>
          <div className={styles.steps}>{['Sources', 'Confidence', 'Capabilities', 'Role fit + coverage', 'Interview probes'].map(step => <span key={step}>{step}</span>)}</div>
        </section>}
        {result && dossier && <>
          <section className={styles.panel}>
            <div className={styles.resultHead}><div><div className={styles.eyebrow}>02 / The result</div><h2>Synthetic candidate A · {label(dossier.role)}</h2><p data-testid="result-status" className={styles.muted}>Completed · synthetic evidence</p></div><button className={styles.button} disabled={busy || dirty} onClick={exportSnapshot}>Export snapshot JSON</button></div>
            <div className={styles.metrics}>
              <div className={styles.metric}><span>Role Capability Index</span><strong data-testid="rci-value">{number(dossier.rci)}</strong><span>Observed capability / 100</span></div>
              <div className={styles.metric}><span>Evidence coverage</span><strong data-testid="coverage-value">{percent(dossier.coverage)}</strong><span>Weighted observability</span></div>
              <div className={styles.metric}><span>Conflicted capabilities</span><strong data-testid="conflict-count">{conflictCount}</strong><span>Signals to investigate</span></div>
            </div>
            {dossier.is_insufficient_evidence && <p className={styles.warning}>Insufficient evidence: coverage is below {percent(result.scoring_config.low_coverage_threshold)}. The RCI describes observed capabilities only; this dossier cannot support a complete ranking.</p>}
            <p className={styles.muted}>{dossier.evidence_records.length} observations · {new Set(dossier.evidence_records.map(e => e.cluster_id)).size} project clusters · scenario: {label(dossier.scenario)}</p>
            {previous && <div className={`${styles.notice} mt-4 mb-0`}><strong>Previous snapshot:</strong> {label(previous.dossier.role)} / {label(previous.dossier.scenario)} — RCI {number(previous.dossier.rci)}, coverage {percent(previous.dossier.coverage)}. {previous.evidence_digest === result.evidence_digest ? 'Evidence unchanged; compare the role or weights.' : 'Evidence inputs changed.'}</div>}
            <details className="mt-4"><summary className="cursor-pointer text-sm">Run identity and reproducibility</summary><p className={styles.hash}>Candidate: {dossier.candidate_id}<br />Run: {dossier.analysis_run_id}<br />Snapshot: {dossier.dossier_id}<br />Evidence + factors SHA-256: {result.evidence_digest}<br />Scenario version: {result.scenario_version}</p><p className={styles.muted}>{result.storage_notice}</p></details>
          </section>
          <section className={styles.panel}>
            <div className={styles.eyebrow}>03 / Separate strength from observability</div><h2>Twelve capabilities, no hidden zeros.</h2>
            <p className={styles.muted}>Intervals use project-cluster bootstrap. With fewer than two independent projects, an interval is not estimable. Select a capability to inspect its evidence.</p>
            <div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>Capability</th><th>Weight</th><th>Estimate</th><th>Coverage</th><th>95% interval</th><th>Conflict</th></tr></thead><tbody>
              {(Object.keys(dossier.capability_estimates) as CapabilityKey[]).map(cap => { const estimate = dossier.capability_estimates[cap]; return <tr key={cap}>
                <td><button aria-label={`Inspect ${label(cap)} evidence`} onClick={() => inspect(cap)}>{label(cap)}</button></td><td>{percent(dossier.role_weights[cap])}</td><td>{number(estimate.estimate)}</td><td>{percent(estimate.coverage_k)}</td><td>{estimate.ci_lower === null || estimate.ci_upper === null ? 'Not estimable' : `${number(estimate.ci_lower)}–${number(estimate.ci_upper)}`}</td><td>{dossier.capability_conflicts[cap].has_meaningful_conflict ? 'Investigate' : '—'}</td>
              </tr>; })}
            </tbody></table></div>
            <details className="mt-4"><summary className="cursor-pointer text-sm">Parsed job requirements ({dossier.role_requirements.length})</summary><div data-testid="parsed-requirements">{dossier.role_requirements.length ? dossier.role_requirements.map(req => <p className={`${styles.muted} mt-2`} key={req.requirement_id}>{req.source_text} → {req.capability_mappings.length ? req.capability_mappings.map(label).join(', ') : 'Unresolved; excluded from weights'} ({req.priority})</p>) : <p className={styles.muted}>No parsed requirements. Canonical role priors are in use.</p>}</div></details>
            <div className={styles.override}>
              <div><label htmlFor="override-cap">Override capability</label><select id="override-cap" value={overrideCap} onChange={e => setOverrideCap(e.target.value as CapabilityKey)}>{Object.keys(dossier.role_weights).map(cap => <option key={cap} value={cap}>{label(cap)}</option>)}</select></div>
              <div><label htmlFor="override-reason">Override justification</label><input id="override-reason" value={justification} onChange={e => setJustification(e.target.value)} maxLength={2000} placeholder="Why should this capability receive all the weight?" /></div>
              <button className={styles.button} disabled={busy || dirty || justification.trim().length < 3} onClick={override}>Apply focused override</button>
            </div>
            <p className={`${styles.muted} mt-2`}>This teaching control assigns 100% weight to one capability. It recalculates the complete dossier without changing the evidence.</p>
            <div data-testid="override-history">{dossier.override_history.map((item, index) => <p key={index} className={`${styles.muted} mt-2`}>Override {index + 1}: {item.justification} · {new Date(item.timestamp).toLocaleString()}</p>)}</div>
          </section>
          <section ref={inspector} data-testid="evidence-inspector" className={styles.panel}>
            <div className={styles.eyebrow}>04 / Follow the provenance</div><h2>{label(selected)}</h2>
            <p className={styles.muted}>Candidate → identity → source → artifact → evidence → capability → role requirement → interview probe. The graph contains {result.graph.nodes.length} nodes and {result.graph.edges.length} relationships; the complete graph is included in the export.</p>
            <div className={`${styles.steps} mb-4`}>{Array.from(new Set(result.graph.nodes.map(node => node.type))).map(type => <span key={type}>{type}: {result.graph.nodes.filter(node => node.type === type).length}</span>)}</div>
            <code className={styles.formula}>Capability = weighted support / confidence sum = {sumWeightedSupport.toFixed(3)} / {sumConfidence.toFixed(3)} = {sumConfidence > 0 ? (sumWeightedSupport / sumConfidence).toFixed(2) : 'Unknown'}</code>
            {selectedEvidence.length === 0 && <p className={styles.notice}>No observations support this capability. Its estimate is unknown.</p>}
            {selectedEvidence.map((evidence, index) => <details key={evidence.evidence_id} className={styles.evidence} open={index === 0}>
              <summary>{evidence.source_family} · support {number(evidence.support_score)} · confidence {percent(evidence.confidence)} · {evidence.is_positive_support ? 'positive observation' : 'negative observation'}</summary>
              <dl><dt>Source</dt><dd>{evidence.source_locator}</dd><dt>Artifact</dt><dd>{evidence.provenance.artifact_path}</dd><dt>Revision</dt><dd>{evidence.immutable_revision}</dd><dt>SHA-256</dt><dd>{evidence.fingerprint}</dd><dt>Extractor</dt><dd>{evidence.provenance.extractor_version}</dd><dt>Project cluster</dt><dd>{evidence.cluster_id}</dd><dt>Observation</dt><dd>{evidence.provenance.raw_support_text}</dd></dl>
              <div className={styles.factors}>{Object.entries(evidence.confidence_factors).map(([factor, value]) => <span key={factor}>{label(factor)}: {value.toFixed(3)}</span>)}</div><p className={styles.muted}>Composite confidence = geometric mean of these six factors. Verification status: {evidence.provenance.verification_status}.</p>
            </details>)}
          </section>
          <section className={styles.panel}><div className={styles.eyebrow}>05 / Prepare the interview</div><h2>Questions with a reason.</h2>
            {dossier.interview_questions.map(question => { const probe = dossier.interview_probes.find(p => p.capability_key === question.target_capability); return <article key={question.question_id} className={styles.question}>
              <h3>#{probe?.rank} · {label(question.target_capability)}</h3><p>{question.question_text}</p><p className={styles.muted}>{question.rationale}</p>
              {probe && <code className={styles.formula}>{probe.role_weight.toFixed(3)} × [0.40 × {probe.coverage_gap_term.toFixed(3)} + 0.35 × {probe.uncertainty_term.toFixed(3)} + 0.25 × {probe.contradiction_term.toFixed(3)}] = {probe.priority_score.toFixed(4)}</code>}
              <p className={styles.muted}>Interviewer guidance: {question.verification_guidance}</p><button className={styles.button} onClick={() => inspect(question.target_capability)}>{question.grounding_evidence_ids.length ? `Inspect ${question.grounding_evidence_ids.length} grounding observations` : 'Inspect the evidence gap'}</button>
            </article>; })}
          </section>
          <details className={styles.panel}><summary className="cursor-pointer">Source calibration and completed stages</summary>
            <div className={styles.tableWrap}><table className={styles.table}><thead><tr><th>Source</th><th>Prior α / β</th><th>Simulated TP / FP</th><th>Posterior</th></tr></thead><tbody>{SOURCES.map(source => { const r = result.reliability[source]; return <tr key={source}><td>{source}</td><td>{r.alpha_prior} / {r.beta_prior}</td><td>{r.true_positive_count} / {r.false_positive_count}</td><td>{r.posterior_mean.toFixed(3)}</td></tr>; })}</tbody></table></div>
            {result.stages.map(stage => <p key={stage.label} className={`${styles.muted} mt-3`}>{stage.label}: {stage.status}. {stage.details}</p>)}
          </details>
        </>}
      </div>
    </div>
    <section id="method" className={styles.section}><div className={styles.eyebrow}>The method / Sections 2.2–2.3</div><h2>Make the reasoning inspectable.</h2><div className={styles.grid}>
      <article className={styles.panel}><h3>Evidence strength and confidence</h3><p>Source reliability uses a Beta posterior. Confidence combines artifact integrity, ownership, recency, verification, extraction specificity, and reliability. Capability is their weighted evidence mean.</p><code className={styles.formula}>r = (TP + α) / (TP + FP + α + β)<br />c = (a · o · t · v · x · r)^(1/6)<br />q = Σ(c · z) / Σc &nbsp; · &nbsp; n_eff = (Σc)² / Σ(c²)</code></article>
      <article className={styles.panel}><h3>Role fit, coverage and contradictions</h3><p>Role weights are normalized with softmax. Coverage measures weighted evidence saturation. The RCI uses observed capabilities only. Opposing observations remain visible through the contradiction diagnostic.</p><code className={styles.formula}>w = softmax(u / T)<br />Coverage = Σ w · min(1, Σc / τ)<br />RCI = Σ_observed(w · q) / Σ_observed(w)<br />D = (positive − negative) / (positive + negative + ε)</code></article>
    </div><p className={`${styles.muted} mt-4`}>Implementation convention: support, capability and RCI use a 0–100 scale; confidence, coverage and probe CI width use 0–1. The prototype adds canonical role priors to JD importance and uses a controlled synonym parser. These configured choices do not reconstruct the manuscript’s unavailable calibration. Cluster intervals describe these simulated observations, not validated uncertainty about real candidates.</p></section>
    <section id="benchmarks" className={styles.section}><div className={styles.eyebrow}>Experiments / Keep the evidence boundaries visible</div><h2>Two experiments. Distinct claims.</h2><div className={styles.grid}>
      <article className={styles.panel}><span className={styles.tag}>Paper benchmark · archived aggregate</span><h3 className="mt-5">28,800 candidate-role evaluations</h3><p>16 seeds × 300 candidates × 6 roles. Reported Spearman ρ = 0.928 ± 0.013. Each candidate is evaluated against all six roles.</p><p className="mt-3">Section 2.6 discloses that original per-seed/per-role outputs and exact calibration are unavailable. This interface does not reproduce that headline result.</p></article>
      <article className={styles.panel}><span className={styles.tag}>Executable prototype experiment</span><h3 className="mt-5">4,800 simulated candidates per mode</h3><p>16 seeds × 6 roles × 50 distinct candidates per role, evaluated under five ablation modes. Recorded full-CCI Spearman ρ ≈ 0.943.</p><code className={styles.formula}>python research/run_paper_experiments.py</code><p>A separate cohort construction and experiment. The controls above illustrate mechanisms; they do not run either benchmark.</p></article>
    </div></section>
    <footer className={styles.footer}>CandidateX · Human interview preparation. Synthetic results do not establish real-world hiring accuracy. {dossier && <details className="mt-3"><summary className="cursor-pointer">Snapshot limitations</summary>{dossier.system_limitations.map(item => <p key={item} className="mt-2">{item}</p>)}</details>}</footer>
  </main>;
}
