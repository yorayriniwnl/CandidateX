'use client';

import { useMemo } from 'react';
import { ArrowDownToLine, ArrowUpRight, Braces, CheckCheck, Cloud, Code2, Database, FileText, GitBranch, Layers3, Network, RotateCcw, ShieldCheck, Users, Waypoints } from 'lucide-react';
import type { CapabilityKey } from '../../types/cci';
import { getAnalysisConfidence, getSourceHealth, type LiveResult } from '../../lib/live-analysis';
import { needsClaimVerification, type ResultClaim } from '../../lib/result-claims';
import { EvidenceStatus } from './EvidenceStatus';
import { capabilityName, dateTime, percent, roleName, score, titleWords, readableAnalysisText } from './format';
import styles from './result.module.css';

export const strengthLabels = { insufficient: 'Insufficient evidence', limited: 'Limited support', moderate: 'Moderate support', well_supported: 'Well supported' };

const capabilityIcons = {
  backend_engineering: Braces, frontend_engineering: Code2, database_engineering: Database,
  devops_cloud: Cloud, machine_learning: Network, data_engineering: GitBranch,
  algorithms_problem_solving: Waypoints, testing_quality: CheckCheck, security: ShieldCheck,
  software_architecture: Layers3, collaboration: Users, documentation_communication: FileText,
};

export function ResultHeader({ result, onNewEvaluation }: { result: LiveResult; onNewEvaluation: () => void }) {
  const repositories = result.sources.filter(s => s.repository_review || (s.files_inspected ?? 0) > 0).length;
  const initials = result.intake.manifest.display_name.trim().split(/\s+/).slice(0, 2).map(name => Array.from(name)[0]).join('');
  function exportDossier() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = `candidatex-${result.dossier.analysis_run_id}.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <header className={styles.header}>
    <div className={styles.eyebrow}>Candidate intelligence <span>/</span> Technical dossier <EvidenceStatus status={result.status} label={result.status === 'partial' ? 'Completed with gaps' : result.status} /></div>
    <div className={styles.titleRow}><div className={styles.identity}><span className={styles.monogram} aria-hidden="true">{initials}</span><div><h1>{result.intake.manifest.display_name}</h1><p><span className={styles.roleTag}>{roleName(result.dossier.role)}</span><span>Target role</span></p></div></div>
      <div className={styles.actions}><button type="button" onClick={onNewEvaluation}><RotateCcw size={14} aria-hidden="true" />Run another analysis</button><button className={styles.primary} type="button" aria-label="Export dossier JSON" onClick={exportDossier}><ArrowDownToLine size={15} aria-hidden="true" />Export dossier</button></div>
    </div>
    <div className={styles.metadata}><span><b>{percent(result.dossier.coverage, 0)}</b> evidence coverage</span><span><b data-testid="source-receipts-count">{result.sources.length}</b> {result.sources.length === 1 ? 'source' : 'sources'}</span><span><b data-testid="repositories-inspected-count">{repositories}</b> {repositories === 1 ? 'repository' : 'repositories'} inspected</span><span>Last analyzed <time dateTime={result.dossier.generated_at}>{dateTime(result.dossier.generated_at)}</time></span></div>
  </header>;
}

export function ExecutiveSummary({ result, claims }: { result: LiveResult; claims: ResultClaim[] }) {
  const estimates = Object.values(result.dossier.capability_estimates);
  const observed = estimates.filter(e => e.is_observed && e.estimate != null);
  const confidence = getAnalysisConfidence(result.dossier, result.analysis, getSourceHealth(result));
  const clusters = new Set(result.dossier.evidence_records.filter(e => e.confidence > 0 && e.cluster_id).map(e => e.cluster_id)).size;
  const conflicts = Object.values(result.dossier.capability_conflicts).filter(c => c.has_meaningful_conflict).length;
  const unknown = estimates.filter(e => !e.is_observed || e.estimate == null).sort((a, b) => (result.dossier.role_weights?.[b.capability_key] ?? 0) - (result.dossier.role_weights?.[a.capability_key] ?? 0));
  const questions = result.dossier.interview_questions;
  const claimsToVerify = claims.filter(c => needsClaimVerification(c.status)).length;
  const rci = result.dossier.rci;
  return <section id="overview" className={styles.snapshot} aria-label="Executive technical snapshot">
    <div className={styles.scoreBlock}><div className={styles.eyebrow}>Role capability</div><div className={styles.scoreDial}><svg viewBox="0 0 160 148" aria-hidden="true"><circle className={styles.dialTrack} cx="80" cy="80" r="66" pathLength="100" strokeDasharray="75 100" transform="rotate(135 80 80)" />{rci != null && <circle className={styles.dialValue} cx="80" cy="80" r="66" pathLength="100" strokeDasharray={`${Math.max(0, Math.min(100, rci)) * .75} 100`} transform="rotate(135 80 80)" />}</svg><div className={styles.score} data-unavailable={rci == null}>{score(rci)}{rci != null && <small>OUT OF 100</small>}</div></div><h2>Role Capability Index</h2><p>Evidence-supported estimate across observed capabilities.</p><div className={styles.coverage}><strong>{percent(result.dossier.coverage, 0)} coverage</strong><span>of role-weighted evidence</span></div><div className={styles.coverageTrack}><i style={{ width: `${Math.max(0, Math.min(100, result.dossier.coverage * 100))}%` }} /></div><small className={styles.boundary}>This is not a probability or hiring recommendation.</small></div>
    <div className={styles.snapshotBody}><div className={styles.strength}><h2>Evidence strength</h2><EvidenceStatus status={confidence.evidence_strength === 'well_supported' ? 'supported' : 'partial'} label={strengthLabels[confidence.evidence_strength]} /></div><p className={styles.explanation}>{confidence.explanation}</p>
      <dl className={styles.stats}><div><dd>{observed.length}<small> / {estimates.length}</small></dd><dt>Observed capabilities</dt><div className={styles.dimensionStrip} aria-hidden="true">{estimates.map(e => <i key={e.capability_key} data-observed={e.is_observed && e.estimate != null} title={`${capabilityName(e.capability_key)}: ${e.is_observed && e.estimate != null ? 'Observed' : 'Unknown'}`} />)}</div></div><div><dd>{unknown.length}</dd><dt>Unknown</dt></div><div><dd>{result.dossier.evidence_records.length}</dd><dt>Evidence records</dt></div><div><dd>{clusters || '—'}</dd><dt>Independent clusters</dt></div><div><dd>{conflicts}</dd><dt>Meaningful conflicts</dt></div></dl>
      <div className={styles.priorities}><div><span className={styles.eyebrow}>Biggest uncertainty</span><p>{unknown.length ? `${unknown.slice(0, 2).map(e => capabilityName(e.capability_key)).join(' and ')}${unknown.length > 2 ? `, plus ${unknown.length - 2} more` : ''} remain unknown.` : confidence.uncertainty_flags.length ? titleWords(confidence.uncertainty_flags[0]) : 'Review confidence ranges and ownership before drawing conclusions.'}</p><a href="#conflicts">Review uncertainty →</a></div><div><span className={styles.eyebrow}>Claims to verify</span><p>{claims.length ? `${claimsToVerify} of ${claims.length} reviewed claims need follow-up.` : 'Claim assessment unavailable. Review the supplied declarations.'}</p><a href="#claims">Review claim verification →</a></div><div><span className={styles.eyebrow}>Interview focus</span><p>{readableAnalysisText(questions[0]?.question_text ?? result.analysis.next_steps[0] ?? 'Request a walkthrough of the candidate’s own work to verify capability and ownership.')}</p><a href="#interview">Open interview plan →</a></div></div>
    </div>
  </section>;
}

export function CapabilityMatrix({ result, selected, onSelect, onInspectEvidence, onInspectCapability }: { result: LiveResult; selected: CapabilityKey | null; onSelect: (key: CapabilityKey | null) => void; onInspectEvidence: (key: CapabilityKey, id: string) => void; onInspectCapability: (key: CapabilityKey) => void }) {
  const estimates = useMemo(() => Object.values(result.dossier.capability_estimates).sort((a, b) => (result.dossier.role_weights?.[b.capability_key] ?? 0) - (result.dossier.role_weights?.[a.capability_key] ?? 0) || (b.estimate ?? -1) - (a.estimate ?? -1)), [result.dossier]);
  const confidence = getAnalysisConfidence(result.dossier, result.analysis, getSourceHealth(result));
  return <section id="capabilities" className={styles.section}>
    <div className={styles.sectionHeading}><div><span className={styles.eyebrow}>01 / Capability intelligence</span><h2>Capability map</h2><p>Ranked by role importance. Select a capability to trace its evidence.</p></div><span>{estimates.length} dimensions</span></div>
    <div className={styles.tableScroll} tabIndex={0} aria-label="Capability estimates; scroll horizontally for more columns"><table className={styles.capabilityTable}><caption className={styles.srOnly}>Role emphasis and observed evidence by capability</caption><thead><tr><th>Capability</th><th>Estimate</th><th>95% interval</th><th>Role importance</th><th>Evidence</th><th>Status</th></tr></thead><tbody>{estimates.map(item => {
      const unknown = !item.is_observed || item.estimate == null;
      const weight = result.dossier.role_weights?.[item.capability_key];
      const conflict = result.dossier.capability_conflicts[item.capability_key]?.has_meaningful_conflict;
      const limited = !unknown && (confidence.evidence_strength !== 'well_supported' || item.ci_lower == null || item.ci_upper == null || item.coverage_k < .35);
      const Icon = capabilityIcons[item.capability_key];
      return <tr key={item.capability_key} data-selected={selected === item.capability_key} data-unknown={unknown}>
        <th scope="row"><button aria-expanded={selected === item.capability_key} aria-controls="capability-detail" onClick={() => onSelect(selected === item.capability_key ? null : item.capability_key)}><span className={styles.capabilityIcon} aria-hidden="true"><Icon size={15} strokeWidth={1.6} /></span>{capabilityName(item.capability_key)} <span className={styles.rowToggle} aria-hidden="true">{selected === item.capability_key ? '−' : '+'}</span></button></th>
        <td><div className={styles.estimate}><b>{unknown ? '—' : score(item.estimate, 0)}</b><div className={`${styles.estimateTrack} ${unknown ? styles.unknownTrack : ''}`}>{!unknown && <i style={{ width: `${Math.max(0, Math.min(100, item.estimate!))}%` }} />}</div></div></td>
        <td>{unknown ? '—' : item.ci_lower != null && item.ci_upper != null ? `${score(item.ci_lower, 0)}–${score(item.ci_upper, 0)}` : 'Not returned'}</td><td><span className={styles.weight}>{weight == null ? 'Unavailable' : percent(weight, 0)}</span></td><td><span className={styles.evidenceCount}>{item.raw_evidence_count}</span></td><td><EvidenceStatus status={unknown ? 'unknown' : conflict ? 'conflict' : limited ? 'partial' : 'supported'} label={unknown ? 'Unknown' : conflict ? 'Conflict' : limited ? 'Limited evidence' : 'Observed'} /></td>
      </tr>;
    })}</tbody></table></div><p className={styles.footnote}>Unknown is not zero. Ranges describe uncertainty; role importance is the returned scoring weight.</p>
    {selected && <CapabilityInspector result={result} capability={selected} onClose={() => onSelect(null)} onSelectEvidence={id => onInspectEvidence(selected, id)} onInspectAll={() => onInspectCapability(selected)} />}
  </section>;
}

function CapabilityInspector({ result, capability, onClose, onSelectEvidence, onInspectAll }: { result: LiveResult; capability: CapabilityKey; onClose: () => void; onSelectEvidence: (id: string) => void; onInspectAll: () => void }) {
  const estimate = result.dossier.capability_estimates[capability];
  const records = result.dossier.evidence_records.filter(e => e.target_capability === capability);
  const claims = result.dossier.claims_corroboration.filter(c => c.target_capability === capability);
  const questions = result.dossier.interview_questions.filter(q => q.target_capability === capability);
  return <div id="capability-detail" className={styles.capabilityDetail} aria-live="polite"><div className={styles.strength}><h3>{capabilityName(capability)}</h3><button onClick={onClose} aria-label="Close capability details">×</button></div><div className={styles.detailColumns}><div><h4>Linked observations</h4>{records.length ? records.slice(0, 4).map(e => <button className={styles.observationLink} key={e.evidence_id} onClick={() => onSelectEvidence(e.evidence_id)}><EvidenceStatus status={e.is_positive_support ? 'observed' : 'conflict'} label={e.is_positive_support ? 'Supporting' : 'Contradicting'} /><span>{e.provenance.raw_support_text}</span><code>{e.provenance.artifact_path} ↗</code></button>) : <p>No usable evidence was returned. This capability remains unknown.</p>}{records.length > 0 && <button className={styles.linkButton} onClick={onInspectAll}>Inspect all {records.length} capability records</button>}</div><div><h4>Claims & interview probes</h4>{claims.slice(0, 3).map(c => <p key={c.claim_id}>{c.claim_text} <EvidenceStatus status={c.status} /></p>)}{questions.slice(0, 2).map(q => <p key={q.question_id}>{q.question_text}</p>)}{!claims.length && !questions.length && <p>No linked claims or questions returned.</p>}<details className={styles.disclosure}><summary>Confidence decomposition</summary><p>Select an observation to inspect its integrity, ownership, recency, verification, depth and source reliability factors.</p><dl className={styles.facts}><div><dt>Independent clusters</dt><dd>{estimate.cluster_count ?? 'Unavailable'}</dd></div><div><dt>Effective evidence</dt><dd>{estimate.effective_evidence_count.toFixed(2)}</dd></div><div><dt>Standard error</dt><dd>{estimate.standard_error.toFixed(3)}</dd></div><div><dt>Dispersion</dt><dd>{estimate.dispersion.toFixed(3)}</dd></div></dl></details></div></div></div>;
}

export function ObservedSignals({ result, onInspect }: { result: LiveResult; onInspect: (id: string) => void }) {
  const signals = useMemo(() => {
    const seen = new Set<string>();
    return [...result.dossier.evidence_records].filter(e => e.is_positive_support && e.confidence > 0).sort((a,b) => b.support_score * b.confidence - a.support_score * a.confidence).filter(e => { const key = `${e.provenance.artifact_path}:${e.target_capability}`; if(seen.has(key)) return false; seen.add(key); return true; }).slice(0,6);
  }, [result.dossier.evidence_records]);
  return <section className={styles.section} aria-label="Observed engineering signals"><div className={styles.sectionHeading}><div><span className={styles.eyebrow}>02 / What the evidence says</span><h2>Observed engineering signals</h2><p>Strongest positive observations by support × confidence. Static signals, not verified mastery.</p></div></div><div className={styles.signalGrid}>{signals.map((e, i) => <button className={styles.signal} key={e.evidence_id} onClick={() => onInspect(e.evidence_id)}><span className={styles.signalIndex}>{String(i + 1).padStart(2,'0')}</span><div><h3>{capabilityName(e.target_capability)}</h3><p>{e.provenance.raw_support_text || 'Observation text unavailable.'}</p><code>{e.provenance.artifact_path || 'Artifact unavailable'}</code><small>Supports {capabilityName(e.target_capability)} <span>Inspect <ArrowUpRight size={13} aria-hidden="true" /></span></small></div></button>)}</div>{!signals.length && <p className={styles.empty}>No attributed supporting observations are available in this run.</p>}</section>;
}
