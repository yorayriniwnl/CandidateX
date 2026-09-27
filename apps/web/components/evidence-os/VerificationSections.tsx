'use client';

import { useState } from 'react';
import type { LiveResult } from '../../lib/live-analysis';
import { getAnalysisConfidence, getSourceHealth, publicUrl } from '../../lib/live-analysis';
import type { CapabilityKey } from '../../types/cci';
import { capabilityName, percent, score, titleWords } from './format';
import { needsClaimVerification, type ResultClaim } from '../../lib/result-claims';
import { EvidenceStatus } from './EvidenceStatus';
import styles from './result.module.css';

const statusHelp: Record<string, string> = {
  supported: 'Supporting evidence was found in the inspected sources; mastery is not established.',
  partial: 'Some of this claim is supported. Scope or ownership still needs verification.',
  unverified: 'No independent verification is available for this declaration.',
  ownership_uncertain: 'Related artifacts exist, but the candidate’s contribution is uncertain.',
  contradicted: 'Returned observations conflict with this claim. Investigate before drawing conclusions.',
  not_observed: 'Not found within the bounded scan. This does not mean the claim is false.',
};
function claimLabel(status: string) {
  const labels: Record<string, string> = { corroborated: 'Supported', repository_support: 'Supported', repository_only: 'Ownership uncertain', public_mention_only: 'Unverified', declaration_only: 'Unverified', not_observed_in_scan: 'Not observed' };
  return labels[status] ?? titleWords(status);
}

export function ClaimVerification({ result, rows, onInspect }: { result: LiveResult; rows: ResultClaim[]; onInspect: (id: string) => void }) {
  const [filter, setFilter] = useState('all');
  const [expanded, setExpanded] = useState<string | null>(null);
  const visible = rows.filter(r => filter === 'all' || needsClaimVerification(r.status));
  return <section id="claims" className={styles.section}><div className={styles.sectionHeading}><div><span className={styles.eyebrow}>03 / Declaration → verification</span><h2>Claim verification</h2><p>Separate what is supported from what still needs a conversation.</p></div><label className={styles.filterLabel}>Show<select aria-label="Filter claims" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All claims</option><option value="review">Needs verification</option></select></label></div>
    {rows.length ? <div className={styles.claimList}><div className={styles.claimColumns}><span>Résumé claim</span><span>Result</span><span>Evidence</span></div>{visible.map(r => <div key={r.id} className={styles.claimRow}><button aria-expanded={expanded === r.id} onClick={()=>setExpanded(expanded === r.id ? null : r.id)}>{r.claim}<span aria-hidden="true">{expanded === r.id ? '−' : '+'}</span></button><EvidenceStatus status={r.status} label={claimLabel(r.status)} explanation={statusHelp[claimLabel(r.status).toLowerCase().replaceAll(' ', '_')] ?? r.explanation} /><span className={styles.claimCount}>{r.count ? `${r.count} evidence ${r.count === 1 ? 'match' : 'matches'}` : 'No independent evidence'}</span>{expanded === r.id && <div className={styles.claimDetail}><p>{r.explanation}</p>{r.ids.slice(0, 6).map(id => <button key={id} className={styles.linkButton} onClick={()=>onInspect(id)}>{result.dossier.evidence_records.find(e=>e.evidence_id===id)?.provenance.artifact_path ?? 'Inspect evidence'} ↗</button>)}{r.ids.length > 6 && <details className={styles.disclosure}><summary>Show {r.ids.length - 6} more linked records</summary><div className={styles.claimMore}>{r.ids.slice(6).map(id => <button key={id} className={styles.linkButton} onClick={()=>onInspect(id)}>{result.dossier.evidence_records.find(e=>e.evidence_id===id)?.provenance.artifact_path ?? 'Inspect evidence'} ↗</button>)}</div></details>}{!r.ids.length && [...new Set(r.paths)].map(url => publicUrl(url) ? <a key={url} href={publicUrl(url)} target="_blank" rel="noreferrer">{url} ↗</a> : null)}</div>}</div>)}</div> : <p className={styles.empty}>No claim-verification records were returned.</p>}
    {!visible.length && rows.length > 0 && <p className={styles.empty}>No claims match this filter.</p>}<p className={styles.footnote}>Not observed ≠ false. Repository matches do not establish ownership, mastery or credential authenticity.</p>
  </section>;
}

export function UncertaintyPanel({ result, onSelectCapability, onInspect }: { result: LiveResult; onSelectCapability: (key: CapabilityKey) => void; onInspect: (id: string) => void }) {
  const confidence = getAnalysisConfidence(result.dossier, result.analysis, getSourceHealth(result));
  const flags: Record<string,string> = { confidence_summary_unavailable: 'Evidence-strength summary unavailable', source_failures: 'Source acquisition failures', interval_unavailable: 'Confidence ranges unavailable', single_cluster: 'Evidence comes from one independent project', source_unscanned: 'Some sources were not inspected', low_role_coverage: 'Limited coverage of the target role' };
  const estimates = Object.values(result.dossier.capability_estimates);
  return <section id="conflicts" className={styles.section}><div className={styles.sectionHeading}><div><span className={styles.eyebrow}>06 / Confidence & gaps</span><h2>Uncertainty</h2><p>Where the evidence ends, the interview begins.</p></div></div>
    <div className={styles.flagLine}>{confidence.uncertainty_flags.map(f=><span key={f}>{flags[f] ?? titleWords(f)}</span>)}</div>
    <div className={styles.uncertaintyRows}>{estimates.map(e=>{
      const unknown = !e.is_observed || e.estimate == null;
      const records = result.dossier.evidence_records.filter(r=>r.target_capability===e.capability_key);
      const uncertainOwnership = records.some(r=>r.confidence_factors.ownership_score == null || r.confidence_factors.ownership_score < .75);
      const conflict = result.dossier.capability_conflicts[e.capability_key];
      return <div key={e.capability_key}><button onClick={()=>onSelectCapability(e.capability_key)}>{capabilityName(e.capability_key)} ↗</button><span>{unknown ? 'Unknown' : `Estimate ${score(e.estimate,0)}`}<small>{unknown ? 'Not enough evidence' : e.ci_lower != null && e.ci_upper != null ? `Confidence range ${score(e.ci_lower,0)}–${score(e.ci_upper,0)}` : 'Confidence range unavailable'}</small></span><div><p>{unknown ? 'No usable estimate within the supplied sources and scan limits.' : e.cluster_count == null ? 'Independent project count unavailable.' : `Evidence from ${e.cluster_count} independent ${e.cluster_count === 1 ? 'project' : 'projects'}.`}{uncertainOwnership ? ' Candidate ownership is partly uncertain.' : ''}{!unknown && e.cluster_count === 1 ? ' Independent corroboration is needed.' : ''}</p>{conflict?.has_meaningful_conflict && <><EvidenceStatus status="conflict" label="Conflicting observations" />{conflict.triggering_evidence_ids?.map(id=><button className={styles.linkButton} key={id} onClick={()=>onInspect(id)}>Inspect conflict evidence ↗</button>)}</>}</div></div>;
    })}</div>
    <details className={styles.disclosure}><summary>Show methodology</summary><p>Capability ranges are returned by the scoring service. Effective evidence discounts dependent observations; it is not a count of files. Missing ranges stay unavailable.</p><div className={styles.tableScroll}><table className={styles.capabilityTable}><thead><tr><th>Capability</th><th>Effective evidence</th><th>Standard error</th><th>Dispersion</th></tr></thead><tbody>{estimates.map(e=><tr key={e.capability_key}><td>{capabilityName(e.capability_key)}</td><td>{e.effective_evidence_count.toFixed(2)}</td><td>{e.standard_error.toFixed(3)}</td><td>{e.dispersion.toFixed(3)}</td></tr>)}</tbody></table></div></details>
  </section>;
}
