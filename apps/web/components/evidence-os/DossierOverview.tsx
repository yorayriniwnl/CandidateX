'use client';

import type { CapabilityKey } from '../../types/cci';
import type { LiveResult } from '../../lib/live-analysis';
import { EvidenceStatus } from './EvidenceStatus';
import { capabilityName, dateTime, percent, roleName, score } from './format';
import styles from './evidence-os.module.css';

export function ExecutiveSummary({ result }: { result: LiveResult }) {
  const estimates = Object.values(result.dossier.capability_estimates);
  const observedCount = estimates.filter(estimate => estimate.is_observed && estimate.estimate !== null).length;
  const meaningfulConflicts = Object.values(result.dossier.capability_conflicts).filter(conflict => conflict.has_meaningful_conflict).length;
  const inspectedRepositories = result.sources.filter(source => source.repository_review || (source.files_inspected ?? 0) > 0).length;
  const sourceCount = result.sources.length;
  const status = result.status === 'partial' ? 'partial' : result.status;

  return (
    <section id="overview" className={styles.overviewSection} aria-labelledby="dossier-title">
      <div className={styles.resultEyebrow}>
        <span>TECHNICAL DOSSIER</span>
        <code>{result.dossier.analysis_run_id}</code>
        <EvidenceStatus status={status} label={status} />
      </div>
      <div className={styles.resultTitleRow}>
        <div>
          <p className={styles.kicker}>CANDIDATE / {roleName(result.dossier.role)}</p>
          <h1 id="dossier-title">{result.intake.manifest.display_name}</h1>
          <p className={styles.resultSubtitle}>Role capability dossier · Generated {dateTime(result.dossier.generated_at)}</p>
        </div>
        <button className={styles.secondaryButton} type="button" onClick={() => {
          const address = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }));
          const anchor = document.createElement('a');
          anchor.href = address;
          anchor.download = `candidatex-${result.dossier.analysis_run_id}.json`;
          anchor.click();
          setTimeout(() => URL.revokeObjectURL(address), 1000);
        }}>Export dossier JSON <span aria-hidden="true">↓</span></button>
      </div>

      <div className={styles.metricStrip}>
        <article className={styles.metricPrimary}>
          <span>ROLE CAPABILITY INDEX</span>
          <strong>{score(result.dossier.rci)}</strong>
          <small>Estimated index across observed role dimensions</small>
        </article>
        <article>
          <span>EVIDENCE COVERAGE</span>
          <strong>{percent(result.dossier.coverage)}</strong>
          <small>Role-weighted evidence coverage</small>
        </article>
        <article>
          <span>CAPABILITIES OBSERVED</span>
          <strong>{observedCount}<i> / {estimates.length}</i></strong>
          <small>Returned capability dimensions</small>
        </article>
        <article>
          <span>SOURCES RETURNED</span>
          <strong data-testid="source-receipts-count">{sourceCount}</strong>
          <small>Source receipts in this run</small>
        </article>
        <article>
          <span>REPOSITORIES INSPECTED</span>
          <strong data-testid="repositories-inspected-count">{inspectedRepositories}</strong>
          <small>Detailed repository receipts</small>
        </article>
      </div>
      <p className={styles.metricDefinition}>
        RCI summarizes estimated capability across observed role dimensions. Evidence coverage describes how much role-weighted evidence was observed. Neither is a hiring probability.
      </p>

      {(result.status === 'partial' || result.dossier.is_insufficient_evidence) && (
        <div className={styles.partialNotice}>
          <EvidenceStatus status="partial" label="Analysis completed with gaps" />
          <p>Review the source receipts and unknown capabilities below. Missing evidence is not a zero capability score.</p>
        </div>
      )}
      {meaningfulConflicts > 0 && (
        <div className={styles.conflictNotice}>
          <EvidenceStatus status="conflict" label={`${meaningfulConflicts} meaningful ${meaningfulConflicts === 1 ? 'conflict' : 'conflicts'}`} />
          <p>Conflicting observations are shown with their supporting evidence in the conflict review.</p>
        </div>
      )}
      <div className={styles.declarationNote}>
        Resume identity and linked accounts are candidate-declared. Static repository signals support technical follow-up; they do not establish mastery or job performance.
      </div>
      {result.analysis.next_steps.length > 0 && <div className={styles.nextSteps}>
        <h2>Next steps returned by analysis</h2>
        <ul>{result.analysis.next_steps.map((step, index) => <li key={`${index}-${step}`}>{step}</li>)}</ul>
      </div>}
    </section>
  );
}

export function CapabilityMatrix({ result, selected, onSelect, onInspectEvidence }: {
  result: LiveResult;
  selected: CapabilityKey | null;
  onSelect: (capability: CapabilityKey) => void;
  onInspectEvidence: (capability: CapabilityKey, evidenceId: string) => void;
}) {
  const estimates = Object.values(result.dossier.capability_estimates);
  return (
    <section id="capabilities" className={styles.contentSection} aria-labelledby="capability-matrix-title">
      <div className={styles.sectionHeader}>
        <div>
          <p className={styles.sectionEyebrow}>01 / ROLE CONTEXT × OBSERVED EVIDENCE</p>
          <h2 id="capability-matrix-title">Capability map</h2>
          <p>Role emphasis is shown only where the analysis returned a weight. Unknown estimates are not zero.</p>
        </div>
        <span className={styles.sectionCount}>{estimates.length} dimensions</span>
      </div>

      <div className={styles.tableViewport}>
        <table className={styles.dataTable}>
          <caption className={styles.srOnly}>Role emphasis and observed evidence by capability</caption>
          <thead><tr>
            <th scope="col">Capability</th><th scope="col">Role weight</th><th scope="col">Estimate</th>
            <th scope="col">Evidence</th><th scope="col">Coverage</th><th scope="col">95% interval</th><th scope="col">Conflict</th>
          </tr></thead>
          <tbody>{estimates.map(item => {
            const isUnknown = !item.is_observed || item.estimate === null;
            const conflict = result.dossier.capability_conflicts[item.capability_key];
            const weight = result.dossier.role_weights?.[item.capability_key];
            const interval = item.ci_lower != null && item.ci_upper != null
              ? `${item.ci_lower.toFixed(1)}–${item.ci_upper.toFixed(1)}` : 'Not returned';
            return (
              <tr key={item.capability_key} className={selected === item.capability_key ? styles.selectedRow : ''}>
                <th scope="row"><button className={styles.rowSelect} type="button" onClick={() => onSelect(item.capability_key)} aria-pressed={selected === item.capability_key}>{capabilityName(item.capability_key)}</button></th>
                <td className={styles.roleWeightCell}>{weight === undefined ? <span>Not returned</span> : <>
                  <span>{percent(weight)}</span>
                  <div className={styles.roleWeightMeter} role="meter" aria-label={`${capabilityName(item.capability_key)} role weight`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(weight * 100)}>
                    <span style={{ width: `${Math.min(100, Math.max(0, weight * 100))}%` }} />
                  </div>
                </>}</td>
                <td className={styles.estimateCell}>{isUnknown ? <EvidenceStatus status="unknown" label="UNKNOWN" /> : item.estimate?.toFixed(1)}</td>
                <td className={styles.numericCell}>{item.raw_evidence_count}<small>{item.effective_evidence_count.toFixed(1)} effective</small></td>
                <td className={styles.numericCell}>{percent(item.coverage_k)}</td>
                <td className={styles.numericCell}>{interval}</td>
                <td>{conflict?.has_meaningful_conflict ? <EvidenceStatus status="conflict" label="meaningful" /> : <span className={styles.muted}>None returned</span>}</td>
              </tr>
            );
          })}</tbody>
        </table>
      </div>

      <ul className={styles.mobileCapabilities} aria-label="Capability estimates">
        {estimates.map(item => {
          const isUnknown = !item.is_observed || item.estimate === null;
          const weight = result.dossier.role_weights?.[item.capability_key];
          const conflict = result.dossier.capability_conflicts[item.capability_key]?.has_meaningful_conflict;
          return <li key={item.capability_key} className={selected === item.capability_key ? styles.mobileCapabilitySelected : ''}>
            <button type="button" onClick={() => onSelect(item.capability_key)} aria-pressed={selected === item.capability_key}>
              <span className={styles.mobileCapabilityName}>{capabilityName(item.capability_key)}<small>{weight === undefined ? 'Role emphasis not returned' : `Role weight ${percent(weight)}`}</small></span>
              <span className={styles.mobileCapabilityValue}>{isUnknown ? 'UNKNOWN' : item.estimate?.toFixed(1)}<small>{item.raw_evidence_count} evidence · {percent(item.coverage_k)} coverage</small></span>
            </button>
            {conflict && <EvidenceStatus status="conflict" label="meaningful conflict" />}
          </li>;
        })}
      </ul>
      {selected && <CapabilityInspector result={result} capability={selected} onSelectEvidence={evidenceId => onInspectEvidence(selected, evidenceId)} />}
    </section>
  );
}

function CapabilityInspector({ result, capability, onSelectEvidence }: { result: LiveResult; capability: CapabilityKey; onSelectEvidence: (evidenceId: string) => void }) {
  const estimate = result.dossier.capability_estimates[capability];
  const conflict = result.dossier.capability_conflicts[capability];
  const evidence = result.dossier.evidence_records.filter(item => item.target_capability === capability);
  const weight = result.dossier.role_weights?.[capability];
  const requirements = result.dossier.role_requirements.filter(requirement => requirement.capability_mappings.includes(capability));
  const unknown = !estimate?.is_observed || estimate.estimate === null;

  return (
    <div className={styles.inspector} aria-live="polite">
      <div className={styles.inspectorHeader}>
        <div><p className={styles.sectionEyebrow}>CAPABILITY INSPECTOR</p><h3>{capabilityName(capability)}</h3></div>
        {unknown ? <EvidenceStatus status="unknown" label="UNKNOWN" /> : <strong className={styles.inspectorScore}>{score(estimate.estimate)}</strong>}
      </div>
      {unknown && <p className={styles.unknownExplanation}>No estimate was returned for this dimension in the supplied sources and scan limits. This is not a zero score or a claim that the candidate lacks the capability.</p>}
      <dl className={styles.inspectorFacts}>
        <div><dt>Role weight</dt><dd>{weight === undefined ? 'Not returned' : percent(weight)}</dd></div>
        <div><dt>Evidence records</dt><dd>{estimate?.raw_evidence_count ?? evidence.length}</dd></div>
        <div><dt>Effective evidence</dt><dd>{estimate ? estimate.effective_evidence_count.toFixed(1) : 'Not returned'}</dd></div>
        <div><dt>Capability coverage</dt><dd>{estimate ? percent(estimate.coverage_k) : 'Not returned'}</dd></div>
        <div><dt>Confidence interval</dt><dd>{estimate?.ci_lower !== null && estimate?.ci_lower !== undefined && estimate.ci_upper !== null ? `${estimate.ci_lower.toFixed(1)}–${estimate.ci_upper.toFixed(1)}` : 'Not returned'}</dd></div>
        <div><dt>Meaningful conflict</dt><dd>{conflict ? conflict.has_meaningful_conflict ? 'Yes' : 'No' : 'Not returned'}</dd></div>
      </dl>
      {requirements.length > 0 && <div className={styles.requirementList}>
        <span>ROLE REQUIREMENTS RETURNED</span>
        {requirements.map(requirement => <p key={requirement.requirement_id}><strong>{requirement.normalized_name}</strong> · {requirement.priority}<small>{requirement.source_text}</small></p>)}
      </div>}
      <details className={styles.diagnosticDetails}>
        <summary>Uncertainty and conflict diagnostics</summary>
        {estimate && <dl><div><dt>Standard error</dt><dd>{estimate.standard_error.toFixed(3)}</dd></div><div><dt>Dispersion</dt><dd>{estimate.dispersion.toFixed(3)}</dd></div><div><dt>Clusters</dt><dd>{estimate.cluster_count ?? 'Not returned'}</dd></div></dl>}
        {conflict && <dl><div><dt>Positive support</dt><dd>{conflict.positive_support_sum.toFixed(2)}</dd></div><div><dt>Negative support</dt><dd>{conflict.negative_support_sum.toFixed(2)}</dd></div><div><dt>Diagnostic</dt><dd>{conflict.contradiction_diagnostic.toFixed(3)}</dd></div></dl>}
      </details>
      <div className={styles.inspectorEvidence}>
        <div><span>WHY THIS ESTIMATE EXISTS</span><span>{evidence.length} linked records</span></div>
        {evidence.length === 0 ? <p>No evidence records were returned for this capability.</p> : <ul>
          {evidence.slice(0, 3).map(item => <li key={item.evidence_id}>
            <EvidenceStatus status={item.is_positive_support ? 'observed' : 'conflict'} label={item.is_positive_support ? 'supporting' : 'contradicting'} />
            <span>{item.provenance.raw_support_text || item.provenance.artifact_path || item.source_locator}</span>
            <code>{item.immutable_revision}</code>
          </li>)}
        </ul>}
        {evidence.length > 0 && <button className={styles.textButton} type="button" onClick={() => onSelectEvidence(evidence[0].evidence_id)}>Inspect all {evidence.length} evidence records <span aria-hidden="true">→</span></button>}
      </div>
    </div>
  );
}
