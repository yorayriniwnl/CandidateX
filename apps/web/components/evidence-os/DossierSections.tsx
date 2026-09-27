'use client';

import { useMemo, useState } from 'react';
import type { CapabilityKey } from '../../types/cci';
import type { LiveResult } from '../../lib/live-analysis';
import { EvidenceStatus } from './EvidenceStatus';
import { capabilityName, dateTime, percent, titleWords } from './format';
import styles from './evidence-os.module.css';

export function ClaimsSection({ result }: { result: LiveResult }) {
  const declared = result.intake.manifest.claimed_skills;
  const skillReport = result.analysis.skills;
  const corroboration = result.dossier.claims_corroboration;
  const credentials = result.analysis.credentials;
  const projects = result.analysis.projects;

  return (
    <section id="claims" className={styles.contentSection} aria-labelledby="claims-title">
      <div className={styles.sectionHeader}>
        <div>
          <p className={styles.sectionEyebrow}>03 / DECLARATIONS × OBSERVATIONS</p>
          <h2 id="claims-title">Claims and corroboration</h2>
          <p>Resume statements remain self-reported unless the response includes separate supporting observations.</p>
        </div>
      </div>

      <div className={styles.subsection}>
        <h3>Declared skills</h3>
        {declared.length === 0 ? <p className={styles.emptyLine}>No skills were extracted from the resume.</p> : <div className={styles.declaredSkills}>
          {declared.map((skill, index) => <span key={`${skill}-${index}`}><EvidenceStatus status="self_reported" tone="neutral" label="self-reported" /><strong>{skill}</strong></span>)}
        </div>}
      </div>

      <div className={styles.subsection}>
        <h3>Skill claim vs. observed sources</h3>
        {skillReport.length === 0 ? <p className={styles.emptyLine}>No skill analysis rows were returned.</p> : <div className={styles.tableViewport}>
          <table className={styles.dataTable}>
            <caption className={styles.srOnly}>Resume skill claims and exact repository or public-page matches</caption>
            <thead><tr><th scope="col">Resume claim</th><th scope="col">Source signal</th><th scope="col">Evidence</th><th scope="col">Status returned</th><th scope="col">Explanation</th></tr></thead>
            <tbody>{skillReport.map((item, index) => <tr key={`${item.skill}-${index}`}>
              <th scope="row">{item.skill}{item.learning && <small className={styles.tableSubtext}>Currently learning · declared</small>}</th>
              <td>{item.evidence.length > 0 ? item.evidence.map((evidence, evidenceIndex) => <span className={styles.claimEvidence} key={`${evidence.url}-${evidenceIndex}`}>
                <strong>{evidence.name}</strong><small>{evidence.path}</small>
                <EvidenceStatus status={evidence.attribution_observed ? 'observed' : 'unknown'} label={evidence.attribution_observed ? 'repository-level attribution signal' : 'attribution not established'} />
              </span>) : item.public_mentions.length > 0 ? <span>{item.public_mentions.join(' · ')}<small>Public text mention; not independent verification.</small></span> : 'No matching source signal returned'}</td>
              <td className={styles.numericCell}>{item.evidence_count}</td>
              <td><EvidenceStatus status={item.status} label={titleWords(item.status)} /></td>
              <td>{item.explanation}</td>
            </tr>)}</tbody>
          </table>
        </div>}
      </div>

      <div className={styles.subsection}>
        <h3>Capability-oriented claim corroboration</h3>
        {corroboration.length === 0 ? <p className={styles.emptyLine}>No claim-corroboration rows were returned. A broader resume claim ledger is not available in this response.</p> : <div className={styles.tableViewport}>
          <table className={styles.dataTable}>
            <caption className={styles.srOnly}>Claim corroboration returned by the live dossier</caption>
            <thead><tr><th scope="col">Claim</th><th scope="col">Capability</th><th scope="col">Status</th><th scope="col">Confidence</th><th scope="col">Evidence references</th><th scope="col">Explanation</th></tr></thead>
            <tbody>{corroboration.map(claim => <tr key={claim.claim_id}>
              <th scope="row">{claim.claim_text}<small className={styles.tableSubtext}><code>{claim.claim_id}</code></small></th>
              <td>{capabilityName(claim.target_capability)}</td>
              <td><EvidenceStatus status={claim.status} label={titleWords(claim.status)} /></td>
              <td className={styles.numericCell}>{percent(claim.confidence)}</td>
              <td>{claim.grounding_evidence_ids.length} records{claim.citation_urls.length > 0 && <small className={styles.tableSubtext}>{claim.citation_urls.join(' · ')}</small>}</td>
              <td>{claim.explanation}</td>
            </tr>)}</tbody>
          </table>
        </div>}
      </div>

      {projects.length > 0 && <div className={styles.subsection}>
        <h3>Project declarations</h3>
        <div className={styles.projectRows}>{projects.map((project, index) => <article key={`${project.title}-${index}`}>
          <div><span className={styles.sectionEyebrow}>PROJECT CLAIM / {String(index + 1).padStart(2, '0')}</span><h4>{project.title || 'Untitled project'}</h4></div>
          <EvidenceStatus status={project.status} label={titleWords(project.status)} />
          {project.description && <p>{project.description}</p>}
          {project.source_urls.length > 0 ? <p>Linked sources: {project.source_urls.join(' · ')}</p> : <p>No source URL was linked in the returned analysis.</p>}
          <small>{project.explanation}</small>
        </article>)}</div>
      </div>}

      {credentials.length > 0 && <div className={styles.subsection}>
        <h3>Credential claims</h3>
        <p className={styles.scopeNote}>A public text match does not authenticate the issuer, recipient, dates, or current validity.</p>
        {credentials.map((credential, index) => <article className={styles.claimLine} key={`${credential.claim}-${index}`}>
          <div><strong>{credential.claim}</strong><small>{credential.explanation}</small></div>
          <EvidenceStatus status={credential.status} label={titleWords(credential.status)} />
          {credential.matching_pages.map((match, matchIndex) => <p key={`${match.url}-${matchIndex}`}>{match.title || match.url} · matched terms: {match.matched_terms.join(', ')} · candidate name present: {match.candidate_name_present ? 'yes' : 'no'}</p>)}
        </article>)}
      </div>}

      {(result.analysis.education.length > 0 || result.analysis.experience.length > 0 || result.analysis.achievements.length > 0) && <details className={styles.diagnosticDetails}>
        <summary>Resume sections · self-reported statements</summary>
        {[
          ['Education', result.analysis.education], ['Experience', result.analysis.experience], ['Achievements', result.analysis.achievements],
        ].map(([label, rows]) => <div className={styles.resumeClaimGroup} key={label as string}>
          <h4>{label as string}</h4>
          {(rows as { claim: string; status: string }[]).length === 0 ? <p>No entries returned.</p> : <ul>{(rows as { claim: string; status: string }[]).map((row, index) => <li key={`${row.claim}-${index}`}><span>{row.claim}</span><EvidenceStatus status={row.status} label={titleWords(row.status)} /></li>)}</ul>}
        </div>)}
      </details>}

      {result.analysis.quantified_claims_to_verify.length > 0 && <div className={styles.subsection}>
        <h3>Quantified claims to verify</h3>
        <p className={styles.scopeNote}>These statements were extracted for follow-up; no numeric claim is independently verified here.</p>
        <ul className={styles.verifyList}>{result.analysis.quantified_claims_to_verify.map((claim, index) => <li key={`${index}-${claim}`}>{claim}</li>)}</ul>
      </div>}
    </section>
  );
}

export function ConflictAndUnknownReview({ result, onSelectCapability, onSelectEvidence }: {
  result: LiveResult;
  onSelectCapability: (capability: CapabilityKey) => void;
  onSelectEvidence: (evidenceId: string) => void;
}) {
  const estimates = Object.values(result.dossier.capability_estimates);
  const unknown = estimates.filter(item => !item.is_observed || item.estimate === null);
  const conflicts = Object.values(result.dossier.capability_conflicts).filter(item => item.has_meaningful_conflict);
  const questionsByCapability = new Map(result.dossier.interview_questions.map(question => [question.target_capability, question]));

  return (
    <section id="conflicts" className={styles.contentSection} aria-labelledby="conflicts-title">
      <div className={styles.sectionHeader}>
        <div><p className={styles.sectionEyebrow}>05 / GAPS & CONTRADICTIONS</p><h2 id="conflicts-title">Unknowns and conflicts</h2>
          <p>Unknown means the bounded run did not observe enough evidence to return an estimate. It is not a zero score or a negative statement about the candidate.</p>
        </div>
        <span className={styles.sectionCount}>{unknown.length} unknown · {conflicts.length} meaningful conflicts</span>
      </div>

      <div className={styles.subsection}>
        <h3>Capabilities without an estimate</h3>
        {unknown.length === 0 ? <p className={styles.emptyLine}>Every returned capability estimate is marked observed. Review its coverage and uncertainty before drawing conclusions.</p> : <ul className={styles.unknownList}>
          {unknown.map(item => {
            const question = questionsByCapability.get(item.capability_key);
            return <li key={item.capability_key}>
              <button type="button" onClick={() => onSelectCapability(item.capability_key)}>{capabilityName(item.capability_key)} <span>Inspect dimension →</span></button>
              <EvidenceStatus status="unknown" label="UNKNOWN" />
              <p>No estimate was returned within the supplied sources and scan limits. This does not establish absence of capability.</p>
              {question && <small>Interview probe returned: {question.question_text}</small>}
            </li>;
          })}
        </ul>}
      </div>

      <div className={styles.subsection}>
        <h3>Meaningful contradictions</h3>
        {conflicts.length === 0 ? <p className={styles.emptyLine}>No meaningful conflicts were flagged in the returned diagnostics.</p> : <div className={styles.conflictRows}>
          {conflicts.map(conflict => {
            const evidence = result.dossier.evidence_records.filter(record => (conflict.triggering_evidence_ids ?? []).includes(record.evidence_id));
            return <article key={conflict.capability_key}>
              <div className={styles.conflictTitle}><div><span className={styles.sectionEyebrow}>CONTRADICTION ANALYSIS</span><h4>{capabilityName(conflict.capability_key)}</h4></div><EvidenceStatus status="conflict" label="meaningful conflict" /></div>
              <dl className={styles.conflictMetrics}>
                <div><dt>Positive support</dt><dd>{conflict.positive_support_sum.toFixed(2)}</dd></div>
                <div><dt>Negative support</dt><dd>{conflict.negative_support_sum.toFixed(2)}</dd></div>
                <div><dt>Contradiction diagnostic</dt><dd>{conflict.contradiction_diagnostic > 0 ? '+' : ''}{conflict.contradiction_diagnostic.toFixed(3)}</dd></div>
              </dl>
              <p>{evidence.length} triggering evidence records returned.</p>
              {evidence.length > 0 ? <ul>{evidence.map(record => <li key={record.evidence_id}>
                <EvidenceStatus status={record.is_positive_support ? 'observed' : 'conflict'} label={record.is_positive_support ? 'positive support' : 'negative support'} />
                <span>{record.provenance.raw_support_text || record.provenance.artifact_path || record.source_locator}</span>
                <button className={styles.textButton} type="button" onClick={() => onSelectEvidence(record.evidence_id)}>Inspect {record.evidence_id.slice(0, 8)}</button>
              </li>)}</ul> : <p className={styles.muted}>The diagnostic did not return the triggering evidence IDs.</p>}
            </article>;
          })}
        </div>}
      </div>
    </section>
  );
}

export function InterviewPlan({ result, onSelectEvidence }: { result: LiveResult; onSelectEvidence: (evidenceId: string) => void }) {
  const [notes, setNotes] = useState<Record<string, string>>({});
  const probeByCapability = useMemo(() => new Map(result.dossier.interview_probes.map(probe => [probe.capability_key, probe])), [result.dossier.interview_probes]);
  const questions = [...result.dossier.interview_questions].sort((left, right) => {
    const rankLeft = probeByCapability.get(left.target_capability)?.rank ?? Number.MAX_SAFE_INTEGER;
    const rankRight = probeByCapability.get(right.target_capability)?.rank ?? Number.MAX_SAFE_INTEGER;
    return rankLeft - rankRight;
  });

  return (
    <section id="interview" className={styles.contentSection} aria-labelledby="interview-title">
      <div className={styles.sectionHeader}>
        <div><p className={styles.sectionEyebrow}>06 / TECHNICAL FOLLOW-UP</p><h2 id="interview-title">Interview plan</h2>
          <p>Questions and probe ranks are returned by the dossier. Use them to investigate evidence and gaps; they are not a hiring recommendation.</p>
        </div>
        <span className={styles.sectionCount}>{questions.length} questions</span>
      </div>
      {questions.length === 0 ? <div className={styles.emptyState}><p>No interview questions were returned for this run.</p></div> : <ol className={styles.interviewList}>
        {questions.map((question, index) => {
          const probe = probeByCapability.get(question.target_capability);
          return <li key={question.question_id}>
            <article>
              <div className={styles.interviewHead}>
                <span className={styles.interviewNumber}>{String(probe?.rank ?? index + 1).padStart(2, '0')}</span>
                <div><span className={styles.sectionEyebrow}>{capabilityName(question.target_capability)}</span><h3>{probe ? `Probe rank ${probe.rank}` : 'Interview question'}</h3></div>
                {probe && <span className={styles.probeScore}>Priority score <b>{probe.priority_score.toFixed(3)}</b></span>}
              </div>
              <blockquote className={styles.interviewQuestion}>{question.question_text}</blockquote>
              <div className={styles.interviewRationale}><div><h4>Why ask</h4><p>{question.rationale}</p></div><div><h4>What to verify</h4><p>{question.verification_guidance}</p></div></div>
              {question.suggested_followups.length > 0 && <details className={styles.diagnosticDetails}><summary>Suggested follow-ups · {question.suggested_followups.length}</summary><ul>{question.suggested_followups.map((item, followupIndex) => <li key={followupIndex}>{item}</li>)}</ul></details>}
              <div className={styles.groundingLine}>
                <span>GROUNDING EVIDENCE</span>
                {question.grounding_evidence_ids.length === 0 ? <p>No evidence record IDs were linked to this question.</p> : <ul>{question.grounding_evidence_ids.map(evidenceId => <li key={evidenceId}><code>{evidenceId}</code><button className={styles.textButton} type="button" onClick={() => onSelectEvidence(evidenceId)}>Inspect evidence →</button></li>)}</ul>}
              </div>
              <label className={styles.notesField}>
                <span>Interviewer notes <small>LOCAL ONLY · CLEARED ON REFRESH OR RUN CHANGE</small></span>
                <textarea value={notes[question.question_id] ?? ''} onChange={event => setNotes(current => ({ ...current, [question.question_id]: event.target.value }))} rows={3} placeholder="Notes remain in this browser session and are not uploaded or saved." />
              </label>
            </article>
          </li>;
        })}
      </ol>}
    </section>
  );
}

export function AuditSection({ result }: { result: LiveResult }) {
  const limitations = result.dossier.system_limitations;
  return (
    <section id="audit" className={styles.contentSection} aria-labelledby="audit-title">
      <div className={styles.sectionHeader}>
        <div><p className={styles.sectionEyebrow}>08 / RUN PROVENANCE</p><h2 id="audit-title">Audit and limitations</h2>
          <p>Request-scoped analysis metadata returned by the live service.</p>
        </div>
      </div>
      <dl className={styles.auditGrid}>
        <div><dt>Analysis run</dt><dd><code>{result.dossier.analysis_run_id}</code></dd></div>
        <div><dt>Dossier ID</dt><dd><code>{result.dossier.dossier_id}</code></dd></div>
        <div><dt>Candidate request ID</dt><dd><code>{result.dossier.candidate_id}</code></dd></div>
        <div><dt>Generated</dt><dd>{dateTime(result.dossier.generated_at)}</dd></div>
        <div><dt>Evidence mode</dt><dd>{result.dossier.evidence_mode ?? 'Not returned'}</dd></div>
        <div><dt>Storage</dt><dd>{result.intake.storage}</dd></div>
      </dl>
      <div className={styles.subsection}>
        <h3>Component versions returned</h3>
        {Object.keys(result.dossier.versions).length === 0 ? <p className={styles.emptyLine}>No versions returned.</p> : <dl className={styles.versionList}>{Object.entries(result.dossier.versions).map(([component, version]) => <div key={component}><dt>{component}</dt><dd><code>{version}</code></dd></div>)}</dl>}
      </div>
      <div className={styles.subsection}>
        <h3>System limitations</h3>
        {limitations.length === 0 ? <p className={styles.emptyLine}>No system limitations were returned.</p> : <ul className={styles.limitationList}>{limitations.map((limitation, index) => <li key={`${index}-${limitation}`}>{limitation}</li>)}</ul>}
        <p className={styles.scopeNote}>The uploaded resume and live result are request-scoped. Export the dossier to retain this response; refresh clears it.</p>
      </div>
    </section>
  );
}
