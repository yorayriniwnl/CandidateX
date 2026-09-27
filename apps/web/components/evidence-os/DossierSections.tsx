'use client';

import { useMemo, useState } from 'react';
import type { LiveResult } from '../../lib/live-analysis';
import { capabilityName, dateTime, readableAnalysisText, readableInterviewRationale } from './format';
import styles from './evidence-os.module.css';

export function InterviewPlan({ result, onSelectEvidence }: { result: LiveResult; onSelectEvidence: (evidenceId: string) => void }) {
  const [visibleCount, setVisibleCount] = useState(3);
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
        <div><p className={styles.sectionEyebrow}>07 / TECHNICAL FOLLOW-UP</p><h2 id="interview-title">Interview plan</h2>
          <p>Questions and probe ranks are returned by the dossier. Use them to investigate evidence and gaps; they are not a hiring recommendation.</p>
        </div>
        <span className={styles.sectionCount}>{questions.length} questions</span>
      </div>
      {questions.length === 0 ? <div className={styles.emptyState}><p>No interview questions were returned for this run.</p></div> : <ol className={styles.interviewList}>
        {questions.slice(0, visibleCount).map((question, index) => {
          const probe = probeByCapability.get(question.target_capability);
          return <li key={question.question_id}>
            <article>
              <div className={styles.interviewHead}>
                <span className={styles.interviewNumber}>{String(probe?.rank ?? index + 1).padStart(2, '0')}</span>
                <div><span className={styles.sectionEyebrow}>{capabilityName(question.target_capability)}</span></div>

              </div>
              <blockquote className={styles.interviewQuestion}>{readableAnalysisText(question.question_text)}</blockquote>
              <div className={styles.interviewRationale}><div><h4>Why ask</h4><p>{readableInterviewRationale(question.rationale)}</p></div><div><h4>What to verify</h4><p>{question.verification_guidance}</p></div></div>
              {question.suggested_followups.length > 0 && <details className={styles.diagnosticDetails}><summary>Suggested follow-ups · {question.suggested_followups.length}</summary><ul>{question.suggested_followups.map((item, followupIndex) => <li key={followupIndex}>{item}</li>)}</ul></details>}
              <div className={styles.groundingLine}>
                <span>GROUNDING EVIDENCE</span>
                {question.grounding_evidence_ids.length === 0 ? <p>No evidence record IDs were linked to this question.</p> : <ul>{question.grounding_evidence_ids.map(evidenceId => <li key={evidenceId}><code>{result.dossier.evidence_records.find(record => record.evidence_id === evidenceId)?.provenance.artifact_path || 'Linked observation'}</code><button className={styles.textButton} type="button" onClick={() => onSelectEvidence(evidenceId)}>Inspect evidence →</button></li>)}</ul>}
              </div>
              <details className={styles.diagnosticDetails}><summary>Interviewer notes</summary><label className={styles.notesField}>
                <span>Interviewer notes <small>LOCAL ONLY · CLEARED ON REFRESH OR RUN CHANGE</small></span>
                <textarea value={notes[question.question_id] ?? ''} onChange={event => setNotes(current => ({ ...current, [question.question_id]: event.target.value }))} rows={3} placeholder="Notes remain in this browser session and are not uploaded or saved." />
              </label></details>
            </article>
          </li>;
        })}
      </ol>}
      {questions.length > visibleCount && <button className={styles.secondaryButton} type="button" onClick={() => setVisibleCount(count => count + 3)}>Show more questions ({questions.length - visibleCount} remaining)</button>}
    </section>
  );
}

export function AuditSection({ result }: { result: LiveResult }) {
  const limitations = result.dossier.system_limitations;
  return (
    <section className={styles.contentSection} aria-labelledby="audit-title">
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
